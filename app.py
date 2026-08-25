import asyncio
import base64
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import streamlit as st
import streamlit.components.v1 as components

APP_NAME = "AungMin Movie Recap"
MODEL_NAME = "gemini-3.6-flash"
PLATFORMS = ("YouTube", "TikTok", "Bilibili", "RedNote", "Facebook", "Generic")
RATIOS = {"YouTube": "16:9", "TikTok": "9:16", "Bilibili": "16:9", "RedNote": "9:16", "Facebook": "1:1", "Generic": "16:9"}
VOICE_NAMES = ("my-MM-NilarNeural", "my-MM-ThihaNeural", "en-US-AriaNeural")
SUPPORTED_DOMAINS = {
    "YouTube": ("youtube.com", "youtu.be"),
    "TikTok": ("tiktok.com",),
    "Bilibili": ("bilibili.com", "b23.tv"),
    "RedNote": ("xiaohongshu.com", "xhslink.com"),
}


@dataclass(frozen=True)
class SourceInfo:
    url: str
    platform: str
    host: str
    name: str


@dataclass
class EditorState:
    speed: float = 1.0
    flip: bool = False
    blur_strength: int = 0
    blur_x: int = 8
    blur_y: int = 12
    blur_w: int = 34
    blur_h: int = 22
    subtitle_position: str = "Bottom"
    subtitle_mode: str = "Burmese + English"
    subtitle_size: int = 34
    subtitle_offset: float = 0.0
    logo_position: str = "Top Right"
    music_name: str = ""


def inspect_source(url: str) -> SourceInfo:
    clean = (url or "").strip()
    parsed = urlparse(clean)
    if not clean or len(clean) > 2048 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Please paste a valid public link beginning with http:// or https://.")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    platform = "Generic"
    for name, domains in SUPPORTED_DOMAINS.items():
        if host in domains or any(host.endswith("." + domain) for domain in domains):
            platform = name
            break
    return SourceInfo(clean, platform, parsed.netloc, parsed.netloc)


def probe_duration(media_path: str) -> float:
    import imageio_ffmpeg
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", media_path], capture_output=True, text=True, timeout=60)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        return 0.0
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def save_uploaded_file(uploaded, prefix: str) -> str:
    suffix = Path(uploaded.name).suffix.lower() or ".mp4"
    path = Path(tempfile.gettempdir()) / f"{prefix}{suffix}"
    path.write_bytes(uploaded.getvalue())
    return str(path)


def download_authorized_source(url: str) -> str:
    import yt_dlp
    workdir = tempfile.mkdtemp(prefix="aungmin-source-")
    output = str(Path(workdir) / "source.%(ext)s")
    options = {
        "outtmpl": output,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([url])
    except Exception as exc:
        raise ValueError(f"Source could not be loaded. Use a public video you own or have permission to process. {exc}") from exc
    videos = [p for p in Path(workdir).glob("source.*") if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}]
    if not videos:
        raise ValueError("The provider did not return a playable video file.")
    target = Path(tempfile.gettempdir()) / "aungmin-link-source.mp4"
    target.write_bytes(videos[0].read_bytes())
    return str(target)


def upload_to_gemini(api_key: str, media_path: str) -> str:
    size = os.path.getsize(media_path)
    suffix = Path(media_path).suffix.lower()
    mime = {".webm": "video/webm", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}.get(suffix, "video/mp4")
    start_payload = json.dumps({}).encode("utf-8")
    start = Request(
        "https://generativelanguage.googleapis.com/upload/v1beta/files",
        data=start_payload,
        headers={
            "x-goog-api-key": api_key.strip(),
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(start, timeout=60) as response:
            upload_url = response.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            raise ValueError("Gemini did not return a file upload URL.")
        with open(media_path, "rb") as media:
            put = Request(
                upload_url,
                data=media.read(),
                headers={
                    "Content-Length": str(size),
                    "X-Goog-Upload-Offset": "0",
                    "X-Goog-Upload-Command": "upload, finalize",
                    "Content-Type": mime,
                },
                method="POST",
            )
            with urlopen(put, timeout=600) as response:
                data = json.loads(response.read().decode("utf-8"))
        return data.get("file", {}).get("uri", "")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise ValueError(f"Gemini video upload failed ({exc.code}). {detail}") from exc
    except URLError as exc:
        raise ValueError("Gemini video upload could not be reached. Try a shorter video.") from exc


def extract_gemini_text(data: dict) -> str:
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()


def generate_recap_bundle(api_key: str, source: SourceInfo, media_path: str, style: str, detail: str, speed: float, flipped: bool) -> dict:
    file_uri = upload_to_gemini(api_key, media_path)
    duration = probe_duration(media_path)
    target = f"{int(duration * 250)} မှ {int(duration * 300)}" if duration else "video ကြာချိန်နှင့် ကိုက်ညီသည့်"
    prompt = f"""ပေးထားသော video ကို အစမှအဆုံး သေချာကြည့်ပါ။ Video မှာ အသံမရှိလျှင် မြင်ကွင်းများကိုသာ အခြေခံပါ။ အသံရှိလျှင် audio/dialogue နဲ့ visual scene နှစ်ခုလုံးကို ပေါင်းစပ်ပါ။ Video ကို speed {speed:.2f}x ဖြင့်ပြင်ထားပြီး {"ဘယ်ညာ flip ပြင်ထားသည်" if flipped else "မူရင်းဦးတည်ချက်အတိုင်းဖြစ်သည်"}။

မြန်မာ movie recap narrator စာမူကို ဖန်တီးပါ။ မူရင်းမှာမပါတဲ့အချက် မထည့်ပါနှင့်။ Scene အစဉ်မလွဲပါနှင့်။ ဇာတ်ကောင်အမည်ကို တိကျစွာသုံးပါ။ ဇာတ်ကောင်အမည်နေရာတွင် မင်း၊ မင်း၏၊ မင်းတို့၊ မင်းရဲ့ ဟူသော နာမ်စားများ မသုံးပါနှင့်။ Output သည် မြန်မာစာဖြင့်သာ ဖြစ်ရမည်။ TTS ဖတ်ရန် သဘာဝကျသော ပုဒ်ဖြတ်ပုဒ်ရပ် သုံးပါ။ Target length သည် တစ်မိနစ် ၂၅၀ မှ ၃၀၀ မြန်မာစာလုံး၊ စုစုပေါင်း {target} ဝန်းကျင် ဖြစ်ရမည်။ Narration style သည် {style} ဖြစ်ရမည်။ Detail level သည် {detail} ဖြစ်ရမည်။

JSON တစ်ခုတည်းကိုသာ ပြန်ပေးပါ။ Markdown မသုံးပါနှင့်။ JSON key သုံးခုကို အောက်ပါအတိုင်း တိတိကျကျသုံးပါ:
{{"recap_bn":"မြန်မာ recap narration စာမူ","subtitle_bn":"မူရင်း video စကားပြော/အသံအကြောင်းအရာကို မြန်မာလို စာတန်းထိုးရန် စာမူ","subtitle_en":"မူရင်း video စကားပြော/အသံအကြောင်းအရာကို အင်္ဂလိပ်လို စာတန်းထိုးရန် စာမူ"}}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}, {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 16000},
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"x-goog-api-key": api_key.strip(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise ValueError(f"Gemini analysis failed ({exc.code}). {detail}") from exc
    except URLError as exc:
        raise ValueError("Gemini could not be reached while analyzing the video.") from exc
    text = extract_gemini_text(data)
    if not text:
        raise ValueError("Gemini returned no text. Try a shorter public or uploaded video.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)
    try:
        bundle = json.loads(cleaned)
    except json.JSONDecodeError:
        bundle = {"recap_bn": text, "subtitle_bn": text, "subtitle_en": ""}
    recap = str(bundle.get("recap_bn", "")).strip()
    if not recap:
        raise ValueError("Gemini returned an empty recap. Try another valid video.")
    return {
        "recap_bn": recap,
        "subtitle_bn": str(bundle.get("subtitle_bn", recap)).strip(),
        "subtitle_en": str(bundle.get("subtitle_en", "")).strip(),
    }


def stamp(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"00:{total // 60:02d}:{total % 60:02d},000"


def make_srt(bundle: dict, duration: float, path: str, offset: float = 0.0, mode: str = "Burmese + English") -> None:
    bn = [line.strip() for line in bundle.get("subtitle_bn", "").splitlines() if line.strip()]
    en = [line.strip() for line in bundle.get("subtitle_en", "").splitlines() if line.strip()]
    recap = [line.strip() for line in bundle.get("recap_bn", "").splitlines() if line.strip()]
    lines = bn or recap or ["AungMin Movie Recap"]
    chunk = max(3.0, (duration or len(lines) * 4) / len(lines))
    with open(path, "w", encoding="utf-8") as handle:
        for index, line in enumerate(lines, 1):
            start = max(0.0, (index - 1) * chunk + offset)
            end = max(start + 1.0, index * chunk + offset)
            english = en[index - 1] if index - 1 < len(en) else ""
            if mode == "Burmese only": english = ""
            if mode == "English only": line = english or line
            caption = line[:220] + (f"\n{english[:220]}" if english and mode == "Burmese + English" else "")
            handle.write(f"{index}\n{stamp(start)} --> {stamp(end)}\n{caption}\n\n")


def create_voiceover(script: str, path: str, voice_name: str) -> None:
    try:
        import edge_tts
        async def save_audio() -> None:
            await edge_tts.Communicate(script[:8000], voice_name).save(path)
        asyncio.run(save_audio())
    except Exception as exc:
        raise ValueError(f"Voiceover generation failed. Check the selected voice or server connection. {exc}") from exc


def render_mp4(source_path: str, srt_path: str, voice_path: str | None, output_path: str, effects: EditorState, ratio: str, music_path: str | None = None) -> None:
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subtitle_path = srt_path.replace("\\", "/").replace(":", "\\:")
    video_filters = [f"subtitles='{subtitle_path}'"]
    if effects.blur_strength > 0:
        video_filters.append(f"boxblur={max(1, effects.blur_strength // 12)}:1")
    if effects.flip:
        video_filters.append("hflip")
    if ratio == "9:16":
        video_filters.append("crop=ih*9/16:ih")
    elif ratio == "1:1":
        video_filters.append("crop=ih:ih")
    if effects.speed != 1.0:
        video_filters.append(f"setpts=PTS/{effects.speed}")
    command = [ffmpeg, "-y", "-i", source_path]
    if voice_path:
        command += ["-i", voice_path]
    if music_path:
        command += ["-i", music_path]
    command += ["-vf", ",".join(video_filters), "-map", "0:v:0"]
    if voice_path and music_path:
        command += ["-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.18[music];[voice][music]amix=inputs=2:duration=shortest[aout]", "-map", "[aout]"]
    elif voice_path:
        command += ["-map", "1:a:0"]
    elif music_path:
        command += ["-map", "2:a:0"]
    else:
        command += ["-map", "0:a:0?"]
    command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-shortest", "-movflags", "+faststart", output_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Rendering timed out. Try a shorter video.") from exc
    if result.returncode != 0:
        raise ValueError(f"MP4 rendering failed: {result.stderr[-700:]}")


def preview_html(media_path: str, state: EditorState, final: bool = False) -> str:
    if not media_path or not Path(media_path).exists():
        return '<div class="empty-preview">Load a source video to see it here.</div>'
    encoded = base64.b64encode(Path(media_path).read_bytes()).decode("ascii")
    mime = "video/mp4" if media_path.lower().endswith(".mp4") else "video/webm"
    transform = "scaleX(-1)" if state.flip else "none"
    opacity = min(0.82, max(0.05, state.blur_strength / 115))
    blur_box = f"left:{state.blur_x}%;top:{state.blur_y}%;width:{state.blur_w}%;height:{state.blur_h}%;opacity:{opacity};"
    label = "FINAL RECAP PREVIEW" if final else "ORIGINAL SOURCE PREVIEW"
    return f"""
    <style>
      html,body{{margin:0;background:#090d1b;overflow:hidden}}
      .stage{{position:relative;height:380px;overflow:hidden;border:1px solid rgba(255,255,255,.16);border-radius:18px;background:#0f172b;display:grid;place-items:center}}
      video{{width:100%;height:100%;object-fit:contain;transform:{transform}}}
      .blurbox{{position:absolute;{blur_box}border:2px solid #70e8d8;background:rgba(112,232,216,.24);box-sizing:border-box;resize:both;overflow:auto;cursor:move}}
      .tag{{position:absolute;left:14px;top:12px;padding:7px 10px;border-radius:8px;background:rgba(5,8,18,.76);color:#f7f8ff;font:700 10px system-ui;letter-spacing:.12em}}
      .hint{{position:absolute;right:14px;bottom:12px;padding:6px 9px;border-radius:7px;background:rgba(5,8,18,.76);color:#b8c0d7;font:600 10px system-ui}}
      .empty-preview{{height:380px;display:grid;place-items:center;color:#c6cde0;background:#10172b;border-radius:18px;font:600 14px system-ui}}
    </style>
    <div class="stage"><video id="v" controls playsinline src="data:{mime};base64,{encoded}"></video><div class="blurbox"></div><div class="tag">{label}</div><div class="hint">{state.speed:.2f}× · {"FLIPPED" if state.flip else "NORMAL"}</div></div>
    <script>const v=document.getElementById('v');v.playbackRate={state.speed};</script>
    """


st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root{color-scheme:dark}
[data-testid="stAppViewContainer"]{background:radial-gradient(circle at 82% 0%,rgba(24,82,92,.42),transparent 32%),radial-gradient(circle at 10% 46%,rgba(63,24,100,.46),transparent 35%),#070a14}
[data-testid="stHeader"]{background:rgba(5,7,16,.72)}
.block-container{max-width:1540px;padding:.65rem clamp(.8rem,2.3vw,2.5rem) 1rem;overflow:hidden}
.brandbar{height:42px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.13);color:#f4f6ff;font-weight:800;letter-spacing:-.03em}
.brandbar small{color:#8de8db;font-size:.64rem;letter-spacing:.16em;text-transform:uppercase}
.workspace{padding-top:.7rem}
.panel{background:linear-gradient(145deg,rgba(22,27,55,.94),rgba(8,13,29,.96));border:1px solid rgba(255,255,255,.16);border-radius:20px;padding:1rem;box-shadow:0 18px 55px rgba(0,0,0,.22)}
.panel-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:.75rem;margin-bottom:.8rem}
.panel-title{color:#f2f4ff;font-size:.68rem;letter-spacing:.18em;text-transform:uppercase;font-weight:850}
.ready{color:#76eadb;font-size:.75rem;white-space:nowrap}
.info{color:#adb6cc;font-size:.76rem;line-height:1.45}
.stage-label{display:flex;align-items:center;justify-content:space-between;color:#dce1ef;font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;font-weight:800;margin:.7rem 0 .45rem}
.section-note{color:#9da7be;font-size:.74rem;line-height:1.42;margin:.35rem 0 .7rem}
div[data-testid="stTextInput"] label,div[data-testid="stSelectbox"] label,div[data-testid="stTextArea"] label,div[data-testid="stSlider"] label,div[data-testid="stFileUploader"] label,div[data-testid="stRadio"] label{color:#e7eaf4!important;font-weight:700!important}
div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea,div[data-baseweb="select"]>div{background:#f4f5f9!important;color:#101422!important;border:0!important;border-radius:10px!important}
div[data-testid="stButton"]>button{min-height:2.45rem;border-radius:10px;background:#17213b;color:#f7f8ff;border:1px solid rgba(255,255,255,.2);font-weight:750}
div[data-testid="stButton"]>button[kind="primary"],button[kind="primaryFormSubmit"]{background:linear-gradient(105deg,#af82ff,#58e1d1);color:#07101b;border:0}
[data-testid="stTabs"] button{color:#98a2ba!important;font-weight:800!important;font-size:.72rem!important}
[data-testid="stTabs"] button[aria-selected="true"]{color:#75eadb!important}
[data-testid="stAlert"]{color:#edf0f8}
@media(max-width:900px){.block-container{overflow:auto}.panel{padding:.8rem}.brandbar small{font-size:.56rem}.stage{height:260px}.empty-preview{height:260px}}
</style>
""", unsafe_allow_html=True)

if "source" not in st.session_state: st.session_state.source = None
if "media_path" not in st.session_state: st.session_state.media_path = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "bundle" not in st.session_state: st.session_state.bundle = None
if "final_video" not in st.session_state: st.session_state.final_video = None
if "editor" not in st.session_state: st.session_state.editor = EditorState()
editor = st.session_state.editor

st.markdown('<div class="brandbar"><div>🎬 &nbsp;AungMin Movie Recap</div><small>ONE-PAGE CREATOR STUDIO · AUTHORIZED MEDIA</small></div>', unsafe_allow_html=True)

left, right = st.columns([1.05, 1.0], gap="large")
with left:
    st.markdown('<div class="workspace panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-head"><div class="panel-title">Source / preview monitor</div><div class="ready">● live workspace</div></div>', unsafe_allow_html=True)
    source_tab, final_tab = st.tabs(["Original source", "Final recap"])
    with source_tab:
        st.markdown('<div class="stage-label"><span>Original video</span><span>01 · SOURCE</span></div>', unsafe_allow_html=True)
        if st.session_state.media_path:
            components.html(preview_html(st.session_state.media_path, editor), height=405, scrolling=False)
        else:
            st.markdown('<div class="empty-preview">Upload a video or load an authorized public link.</div>', unsafe_allow_html=True)
    with final_tab:
        st.markdown('<div class="stage-label"><span>Edited recap output</span><span>04 · FINISH</span></div>', unsafe_allow_html=True)
        if st.session_state.final_video:
            final_path = str(Path(tempfile.gettempdir()) / "aungmin-final-preview.mp4")
            Path(final_path).write_bytes(st.session_state.final_video)
            components.html(preview_html(final_path, editor, final=True), height=405, scrolling=False)
            st.download_button("Download final MP4", st.session_state.final_video, file_name="aungmin-movie-recap.mp4", mime="video/mp4", use_container_width=True)
        else:
            st.markdown('<div class="empty-preview">Render the recap to unlock the final preview.</div>', unsafe_allow_html=True)
    if st.session_state.source:
        duration = probe_duration(st.session_state.media_path) if st.session_state.media_path else 0
        st.markdown(f'<div class="info" style="margin-top:.7rem">Loaded: <b>{st.session_state.source.platform}</b> · {st.session_state.source.name} · {duration:.1f}s · Original source remains available for comparison.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="workspace panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-head"><div class="panel-title">Production control room</div><div class="ready">● 01–04 selectable</div></div>', unsafe_allow_html=True)
    tabs = st.tabs(["01 · Source", "02 · Recap", "03 · Voice", "04 · Finish"])
    with tabs[0]:
        mode = st.radio("Input type", ["Upload video", "Paste video link"], horizontal=True, key="input_mode")
        uploaded = st.file_uploader("Upload video file", type=["mp4", "mov", "webm", "mkv"], key="source_upload") if mode == "Upload video" else None
        source_url = st.text_input("Video link", placeholder="YouTube · TikTok · Bilibili · RedNote · public URL", key="source_url") if mode == "Paste video link" else ""
        st.caption("Public/authorized media only. Link loading depends on provider access rules.")
        if st.button("Load original video", type="primary", use_container_width=True):
            try:
                if mode == "Upload video":
                    if not uploaded: raise ValueError("Choose a video file first.")
                    st.session_state.media_path = save_uploaded_file(uploaded, "aungmin-uploaded-source")
                    st.session_state.source = SourceInfo(f"upload://{uploaded.name}", "Upload", uploaded.name, uploaded.name)
                else:
                    source = inspect_source(source_url)
                    with st.spinner("Loading the original source video…"):
                        st.session_state.media_path = download_authorized_source(source.url)
                    st.session_state.source = source
                st.session_state.final_video = None
                st.session_state.bundle = None
                st.success("Original video loaded. Preview is ready on the left.")
            except (ValueError, ImportError) as exc:
                st.error(str(exc))
    with tabs[1]:
        style = st.selectbox("Recap narration style", ["Cinematic narrator", "Conversational", "Dramatic", "Calm"], key="recap_style")
        detail = st.select_slider("Scene coverage", ["Essential", "Balanced", "Scene-by-scene"], value="Scene-by-scene", key="scene_detail")
        st.markdown('<div class="section-note">အသံမပါလျှင် AI က မြင်ကွင်းများကို ကြည့်ပြီးရေးမည်။ အသံပါလျှင် မြင်ကွင်းနှင့် dialogue/audio အကြောင်းအရာ နှစ်မျိုးလုံးကို ပေါင်းစပ်ရေးမည်။</div>', unsafe_allow_html=True)
        if st.button("Generate Burmese recap", type="primary", use_container_width=True):
            if not st.session_state.media_path or not st.session_state.source:
                st.error("Load the original video first. API key is used only when generating the recap.")
            elif not st.session_state.api_key:
                st.error("Enter your Google AI Studio API key in 01 · Source before generating.")
            else:
                with st.spinner("Analyzing video visuals/audio and writing Burmese recap…"):
                    try:
                        st.session_state.bundle = generate_recap_bundle(st.session_state.api_key, st.session_state.source, st.session_state.media_path, style, detail, editor.speed, editor.flip)
                        st.success("Burmese recap, Burmese subtitle, and English subtitle drafts are ready.")
                    except (ValueError, ImportError) as exc:
                        st.error(str(exc))
        if st.session_state.bundle:
            st.text_area("Editable Burmese recap", st.session_state.bundle["recap_bn"], height=170, key="editable_recap")
            st.caption("Edit this narration before rendering. Changes are applied to the voiceover and subtitle timing.")
    with tabs[2]:
        voice_name = st.selectbox("Voice profile", VOICE_NAMES, index=0, key="voice_name")
        audio_speed = st.slider("Narration speed", .75, 1.5, 1.0, .05, key="audio_speed")
        st.markdown('<div class="section-note">Burmese recap voiceover ကိုရွေးထားတဲ့ voice profile နဲ့ ထုတ်မည်။ မူရင်းအသံကို music နှင့် narration အဖြစ် မရောမီ သီးခြားထိန်းမည်။</div>', unsafe_allow_html=True)
    with tabs[3]:
        preset = st.selectbox("Authorized-media edit preset", ["Manual", "Cinematic crop", "Vertical short", "Mirror + punchy speed"], key="edit_preset")
        editor.speed = st.slider("Video speed", .5, 2.0, editor.speed, .05, key="video_speed")
        editor.flip = st.checkbox("Horizontal flip", editor.flip, key="video_flip")
        st.markdown('<div class="section-note">ဒီ controls တွေက ကိုယ်ပိုင်/ခွင့်ပြုချက်ရ media အတွက် creative edit ဖြစ်ပြီး copyrighted media ကို copyright-free မလုပ်ပေးပါ။</div>', unsafe_allow_html=True)
        editor.blur_strength = st.slider("Blur strength", 0, 100, editor.blur_strength, key="blur_strength")
        blur_cols = st.columns(4)
        editor.blur_x = blur_cols[0].number_input("Blur X %", 0, 90, editor.blur_x, key="blur_x")
        editor.blur_y = blur_cols[1].number_input("Blur Y %", 0, 90, editor.blur_y, key="blur_y")
        editor.blur_w = blur_cols[2].number_input("Blur W %", 5, 100, editor.blur_w, key="blur_w")
        editor.blur_h = blur_cols[3].number_input("Blur H %", 5, 100, editor.blur_h, key="blur_h")
        editor.subtitle_mode = st.selectbox("Subtitle layers", ["Burmese + English", "Burmese only", "English only"], key="subtitle_mode")
        editor.subtitle_position = st.selectbox("Subtitle position", ["Bottom", "Middle", "Top"], key="subtitle_position")
        editor.subtitle_size = st.slider("Subtitle size", 18, 64, editor.subtitle_size, key="subtitle_size")
        editor.subtitle_offset = st.slider("Subtitle timing offset", -3.0, 3.0, editor.subtitle_offset, .1, key="subtitle_offset")
        output_platform = st.selectbox("Output format", PLATFORMS, format_func=lambda item: f"{item} · {RATIOS[item]}", key="output_platform")
        music = st.file_uploader("Background music", type=["mp3", "wav", "m4a"], key="background_music")
        music_path = save_uploaded_file(music, "aungmin-music") if music else None
        st.markdown('<div class="section-note">Preview ထဲက turquoise rectangle က manual blur region ကိုပြသည်။ လက်ရှိ UI မှာ X/Y/W/H နဲ့ ချိန်နိုင်ပြီး render မှာ blur strength ကို အသုံးချမည်။</div>', unsafe_allow_html=True)
        if st.button("Render final recap video", type="primary", use_container_width=True):
            if not st.session_state.bundle:
                st.error("Generate and review the Burmese recap first.")
            elif not st.session_state.media_path:
                st.error("Load the original video first.")
            else:
                with st.spinner("Rendering voiceover, bilingual subtitles, effects, and MP4 preview…"):
                    try:
                        with tempfile.TemporaryDirectory() as workdir:
                            srt_path = str(Path(workdir) / "captions.srt")
                            voice_path = str(Path(workdir) / "voice.mp3")
                            output_path = str(Path(workdir) / "aungmin-recap.mp4")
                            duration = probe_duration(st.session_state.media_path)
                            make_srt(st.session_state.bundle, duration, srt_path, editor.subtitle_offset, editor.subtitle_mode)
                            create_voiceover(st.session_state.bundle["recap_bn"], voice_path, voice_name)
                            render_mp4(st.session_state.media_path, srt_path, voice_path, output_path, editor, RATIOS[output_platform], music_path)
                            st.session_state.final_video = Path(output_path).read_bytes()
                        st.success("Final MP4 ready. Open the Final recap tab on the left before downloading.")
                    except (ValueError, ImportError) as exc:
                        st.error(str(exc))
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="info" style="margin-top:.5rem;text-align:center">Use only media you own or have permission to process. Editing transformations do not remove copyright; provider access and download behavior depend on platform rules.</div>', unsafe_allow_html=True)
