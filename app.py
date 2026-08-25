import asyncio
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import streamlit as st

APP_NAME = "AungMin Movie Recap"
APP_TAGLINE = "URL-first cinematic recap studio"
PLATFORMS = ("YouTube", "TikTok", "Bilibili", "RedNote", "Facebook")
RATIOS = {"YouTube": "16:9", "TikTok": "9:16", "Bilibili": "16:9", "RedNote": "9:16", "Facebook": "1:1"}
OUTPUT_FORMATS = ("MP4", "WAV", "SRT")
DEFAULT_VOICES = ("Chiron", "Wunna", "Zaw", "Aung", "Thiha")
DEFAULT_LANGUAGES = ("Burmese", "English", "Thai", "Japanese", "Korean", "Chinese")
DEFAULT_VOICE_STYLES = ("Cinematic narrator", "Conversational", "Dramatic", "Calm")
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

@dataclass
class EffectsState:
    subtitle_mode: str = "Burn (Hardsub)"
    subtitle_position: str = "Bottom"
    subtitle_size: int = 38
    logo_position: str = "Top Right"
    blur_strength: int = 0
    music_name: str = ""

def inspect_source(url: str) -> SourceInfo:
    clean = (url or "").strip()
    parsed = urlparse(clean)
    if not clean or len(clean) > 2048 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Paste a valid public URL beginning with http:// or https://.")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    platform = "Generic"
    for name, domains in SUPPORTED_DOMAINS.items():
        if host in domains or any(host.endswith("." + domain) for domain in domains):
            platform = name
            break
    return SourceInfo(clean, platform, parsed.netloc)

def recap_prompt(source: SourceInfo, language: str, style: str, voice: str, mode: str) -> str:
    return (f"SOURCE: {source.url}\nMODE: {mode}\nLANGUAGE: {language}\nVOICE: {voice}\nSTYLE: {style}\n\n"
            "Write a concise, cinematic movie-recap narration with a strong hook, clear scene order, "
            "and a closing line. Keep the narration suitable for subtitles.")

def export_metadata(source: SourceInfo, export_format: str, effects: EffectsState) -> str:
    return json.dumps({"format": export_format, "source": source.url, "effects": effects.__dict__}, indent=2)

def generate_gemini_recap(api_key: str, source: SourceInfo, language: str, style: str, voice: str, mode: str) -> str:
    if source.platform != "YouTube":
        return "This first live adapter supports public YouTube URLs. TikTok, Bilibili, and RedNote adapters will be added after the YouTube flow is verified."
    payload = {"model": "gemini-2.5-flash", "input": [{"type": "text", "text": f"Create a cinematic movie recap narration in {language}. Use a {style} tone for the {voice} voice. Return only the narration with scene order and timestamps when useful. Mode: {mode}."}, {"type": "video", "uri": source.url}]}
    request = Request("https://generativelanguage.googleapis.com/v1beta/interactions", data=json.dumps(payload).encode("utf-8"), headers={"x-goog-api-key": api_key.strip(), "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ValueError(f"Gemini API rejected the request ({exc.code}). Check the key, model access, and that the YouTube video is public. {detail}") from exc
    except URLError as exc:
        raise ValueError("Gemini could not be reached. Check the Streamlit connection and try again.") from exc
    if data.get("output_text"):
        return data["output_text"]
    for item in data.get("outputs", []):
        if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
            return item["text"]
    raise ValueError("Gemini returned no narration text. Try another public YouTube video.")

def download_authorized_source(url: str, workdir: str) -> str:
    import yt_dlp
    output = str(Path(workdir) / "source.%(ext)s")
    options = {"outtmpl": output, "format": "bv*+ba/b", "merge_output_format": "mp4", "noplaylist": True, "quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([url])
    except Exception as exc:
        raise ValueError(f"Source download failed. Use a public video you own or have permission to process. {exc}") from exc
    candidates = sorted(Path(workdir).glob("source.*"))
    videos = [p for p in candidates if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}]
    if not videos:
        raise ValueError("No playable video file was returned by the source provider.")
    return str(videos[0])

def make_srt(script: str, path: str) -> None:
    lines = [line.strip() for line in script.splitlines() if line.strip() and not line.startswith("SOURCE:") and not line.startswith("MODE:")]
    lines = lines[:120] or ["AungMin Movie Recap"]
    with open(path, "w", encoding="utf-8") as handle:
        for index, line in enumerate(lines, 1):
            start = (index - 1) * 4
            end = start + 4
            def stamp(seconds: int) -> str:
                return f"00:{seconds // 60:02d}:{seconds % 60:02d},000"
            handle.write(f"{index}\n{stamp(start)} --> {stamp(end)}\n{line[:160]}\n\n")

def create_voiceover(script: str, path: str, language: str) -> None:
    try:
        import edge_tts
        voice = "my-MM-NilarNeural" if language == "Burmese" else "en-US-AriaNeural"
        async def save_audio() -> None:
            await edge_tts.Communicate(script[:6000], voice).save(path)
        asyncio.run(save_audio())
    except Exception as exc:
        raise ValueError(f"Voiceover generation failed. Check the server connection and try again. {exc}") from exc

def render_mp4(source_path: str, srt_path: str, voice_path: str | None, output_path: str, effects: EffectsState, ratio: str) -> None:
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subtitle_path = srt_path.replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{subtitle_path}'"
    if effects.blur_strength > 0:
        vf += f",boxblur={max(1, effects.blur_strength // 12)}:1"
    if ratio == "9:16":
        vf += ",crop=ih*9/16:ih"
    elif ratio == "1:1":
        vf += ",crop=ih:ih"
    command = [ffmpeg, "-y", "-i", source_path]
    if voice_path:
        command += ["-i", voice_path]
    command += ["-vf", vf, "-map", "0:v:0"]
    if voice_path:
        command += ["-map", "1:a:0", "-shortest"]
    else:
        command += ["-map", "0:a:0?", "-shortest"]
    command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart", output_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Rendering timed out. Try a shorter video.") from exc
    if result.returncode != 0:
        raise ValueError(f"MP4 rendering failed: {result.stderr[-600:]}")

st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root{color-scheme:dark} [data-testid="stAppViewContainer"]{background:radial-gradient(circle at 82% 4%,rgba(25,78,91,.55),transparent 32%),radial-gradient(circle at 12% 48%,rgba(48,20,83,.5),transparent 35%),#070913}[data-testid="stHeader"]{background:rgba(5,7,16,.78)}.block-container{max-width:1500px;padding:1.25rem clamp(1rem,4vw,4rem) 4rem}.brandbar{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.13);padding:.4rem 0 1.2rem}.brandmark{color:#f4f5ff;font-size:1rem;font-weight:750;letter-spacing:-.03em}.eyebrow{color:#75eadb;font-size:.7rem;letter-spacing:.28em;text-transform:uppercase;font-weight:700}.hero{padding:clamp(1.5rem,5vw,4.2rem) 0 2rem}.hero h1{font-size:clamp(3.2rem,8vw,7.8rem);line-height:.86;letter-spacing:-.085em;margin:.9rem 0 1.35rem;color:#f8f9ff}.hero h1 span{background:linear-gradient(100deg,#f9f8ff 30%,#c9a9ff 60%,#5fe9d6 94%);-webkit-background-clip:text;color:transparent}.hero p{color:#c0c4d4;font-size:1.05rem;line-height:1.7;max-width:530px}.panel{background:linear-gradient(145deg,rgba(23,27,55,.93),rgba(10,15,33,.95));border:1px solid rgba(255,255,255,.16);border-radius:22px;padding:1.15rem;box-shadow:0 22px 70px rgba(0,0,0,.26)}.panel-head{display:flex;justify-content:space-between;gap:1rem;align-items:center;padding-bottom:.9rem;border-bottom:1px solid rgba(255,255,255,.1);margin-bottom:1rem}.panel-title{color:#f0f2fb;font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;font-weight:800}.ready{color:#74ead9;font-size:.78rem;white-space:nowrap}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:.45rem;margin:.8rem 0 1rem}.flow span{color:#8990a7;font-size:.68rem;padding:.55rem .4rem;border-bottom:2px solid rgba(255,255,255,.12);text-align:center}.flow .on{color:#74ead9;border-color:#74ead9}.previewbox{min-height:360px;display:flex;align-items:center;justify-content:center;text-align:center;border:1px dashed rgba(255,255,255,.22);border-radius:16px;background:linear-gradient(145deg,#141a31,#081923);color:#d7dbea;padding:1.2rem}.previewbox strong{color:#fff}.play{width:58px;height:58px;border-radius:50%;display:grid;place-items:center;margin:0 auto 1rem;color:#07101a;background:linear-gradient(135deg,#b58cff,#5de4d4);font-size:1.35rem}.section-label{color:#7a829c;text-transform:uppercase;letter-spacing:.18em;font-size:.68rem;margin:.1rem 0 .55rem;font-weight:800}.metricrow{display:flex;gap:1.6rem;margin:2rem 0 0}.metric b{color:#fff;font-size:1.3rem}.metric span{display:block;color:#9ca3b7;font-size:.68rem;letter-spacing:.12em;margin-top:.2rem}.small{color:#aeb4c5;font-size:.8rem;line-height:1.5}div[data-testid="stTextInput"] label,div[data-testid="stSelectbox"] label,div[data-testid="stTextArea"] label,div[data-testid="stSlider"] label,div[data-testid="stFileUploader"] label{color:#dfe3f0!important;font-weight:650!important}div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea,div[data-baseweb="select"]>div{background:#f5f6fa!important;color:#111526!important;border:0!important;border-radius:11px!important}div[data-testid="stTextInput"] input::placeholder{color:#6f7585!important}div[data-testid="stButton"]>button{min-height:2.65rem;border-radius:11px;background:#171e37;color:#f8f9ff;border:1px solid rgba(255,255,255,.2);font-weight:700}div[data-testid="stButton"]>button[kind="primary"],button[kind="primaryFormSubmit"]{background:linear-gradient(105deg,#af80ff,#55e1d1);color:#07101b;border:0}[data-testid="stAlert"]{color:#e9edf7}@media(max-width:800px){.block-container{padding:.8rem 1rem 3rem}.hero{padding-top:1.7rem}.hero h1{font-size:clamp(3.4rem,17vw,5.4rem)}.hero p{font-size:.96rem}.previewbox{min-height:220px}.flow{grid-template-columns:repeat(2,1fr)}.metricrow{gap:1rem}.metric b{font-size:1.05rem}}
</style>
""", unsafe_allow_html=True)

for name, default in (("source", None), ("script", ""), ("effects", EffectsState()), ("preview_ready", False), ("final_video", None)):
    if name not in st.session_state:
        st.session_state[name] = default

st.markdown(f'<div class="brandbar"><div class="brandmark">🎬 &nbsp;{APP_NAME}</div><div class="small">PRIVATE CREATOR WORKSPACE · v0.2</div></div>', unsafe_allow_html=True)
left, right = st.columns([1.08, 1], gap="large")
with left:
    st.markdown('<div class="hero"><div class="eyebrow">Cinematic intelligence</div><h1>Turn stories<br>into <span>cinema.</span></h1>', unsafe_allow_html=True)
    st.markdown(f'<p>{APP_TAGLINE}. Paste an authorized video link, shape the recap, review the final cut, and export only when you are ready.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="metricrow"><div class="metric"><b>01</b><span>SOURCE</span></div><div class="metric"><b>02</b><span>RECAP</span></div><div class="metric"><b>03</b><span>CRAFT</span></div><div class="metric"><b>∞</b><span>POSSIBILITY</span></div></div>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="panel"><div class="panel-head"><div class="panel-title">Production flow</div><div class="ready">● ready</div></div><div class="flow"><span class="on">01 · Source</span><span>02 · Recap</span><span>03 · Voice</span><span>04 · Finish</span></div>', unsafe_allow_html=True)
    with st.form("source_form"):
        st.markdown('<div class="section-label">Authorized source</div>', unsafe_allow_html=True)
        url = st.text_input("Video link", placeholder="YouTube · TikTok · Bilibili · RedNote")
        a, b = st.columns(2)
        with a: mode = st.selectbox("Workflow", ["AI Recap", "Subtitle Only"])
        with b: platform = st.selectbox("Output", PLATFORMS, format_func=lambda x: f"{x} · {RATIOS[x]}")
        key = st.text_input("Google AI Studio API key", type="password", help="Use your own key. Never commit it to GitHub.")
        submitted = st.form_submit_button("Fetch source & continue", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
if submitted:
    if not key.strip(): st.error("Google AI Studio API key is required for the BYOK workflow.")
    else:
        try: st.session_state.source = inspect_source(url); st.session_state.api_ready = True; st.session_state.api_key = key.strip(); st.success(f"Source accepted · {st.session_state.source.platform} · controls unlocked")
        except ValueError as exc: st.error(str(exc))
if st.session_state.source:
    st.markdown('<div style="height:1.2rem"></div>', unsafe_allow_html=True)
    preview_col, controls_col = st.columns([1.08, .92], gap="large")
    with preview_col:
        st.markdown('<div class="panel"><div class="panel-head"><div class="panel-title">Source monitor</div><div class="ready">● connected</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="previewbox"><div><div class="play">▶</div><strong>{st.session_state.source.platform} source ready</strong><br><span class="small">{st.session_state.source.host}</span><br><br><span class="small">The authorized source adapter will fetch a playable stream here.</span></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with controls_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        tabs = st.tabs(["Voice", "Effects", "Advanced"])
        with tabs[0]:
            voice = st.selectbox("Voice profile", DEFAULT_VOICES); language = st.selectbox("Target language", DEFAULT_LANGUAGES); style = st.selectbox("Narration style", DEFAULT_VOICE_STYLES); speed = st.slider("Audio speed", .75, 1.5, 1.0, .05)
        with tabs[1]:
            effects = st.session_state.effects; effects.subtitle_mode = st.selectbox("Subtitle mode", ["Burn (Hardsub)", "File (.srt)"]); effects.subtitle_position = st.selectbox("Subtitle position", ["Bottom", "Middle", "Custom"]); effects.subtitle_size = st.slider("Subtitle size", 20, 64, effects.subtitle_size); effects.logo_position = st.selectbox("Logo position", ["Top Left", "Top Right", "Bottom Left", "Bottom Right"]); effects.blur_strength = st.slider("Blur masks", 0, 100, effects.blur_strength); music = st.file_uploader("Background music", type=["mp3", "wav", "m4a"], key="music"); effects.music_name = music.name if music else effects.music_name
        with tabs[2]:
            intro = st.checkbox("Add intro", False); outro = st.checkbox("Add outro", False); auto_color = st.checkbox("Auto color grade", True); flip = st.checkbox("Flip video", False)
        generate = st.button("Generate recap plan", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    if generate:
        with st.spinner("Asking Gemini to analyze the public video…"):
            try:
                st.session_state.script = generate_gemini_recap(st.session_state.get("api_key", ""), st.session_state.source, language, style, voice, mode)
                st.session_state.preview_ready = False
                st.success("Gemini recap ready. Edit the narration, then start processing.")
            except ValueError as exc:
                st.error(str(exc))
if st.session_state.script:
    st.markdown('<div style="height:1.2rem"></div>', unsafe_allow_html=True)
    script_col, final_col = st.columns([1, 1], gap="large")
    with script_col:
        st.markdown('<div class="panel"><div class="panel-head"><div class="panel-title">Recap script desk</div><div class="ready">● editable</div></div>', unsafe_allow_html=True)
        st.session_state.script = st.text_area("Edit narration before processing", st.session_state.script, height=240)
        if st.button("Start processing", type="primary", use_container_width=True):
            with st.spinner("Downloading, creating subtitles, generating voiceover, and rendering MP4…"):
                try:
                    with tempfile.TemporaryDirectory() as workdir:
                        source_path = download_authorized_source(st.session_state.source.url, workdir)
                        srt_path = str(Path(workdir) / "captions.srt")
                        voice_path = str(Path(workdir) / "voice.mp3")
                        output_path = str(Path(workdir) / "aungmin-recap.mp4")
                        make_srt(st.session_state.script, srt_path)
                        create_voiceover(st.session_state.script, voice_path, language)
                        render_mp4(source_path, srt_path, voice_path, output_path, st.session_state.effects, RATIOS[platform])
                        st.session_state.final_video = Path(output_path).read_bytes()
                    st.session_state.preview_ready = True
                    st.success("MP4 rendering complete. Review the final preview before download.")
                except (ValueError, ImportError) as exc:
                    st.session_state.preview_ready = False
                    st.error(str(exc))
        st.markdown('</div>', unsafe_allow_html=True)
    with final_col:
        st.markdown('<div class="panel"><div class="panel-head"><div class="panel-title">Final preview gate</div><div class="ready">● review before export</div></div>', unsafe_allow_html=True)
        if st.session_state.preview_ready and st.session_state.get("final_video"):
            st.video(st.session_state.final_video); st.caption("Preview gate passed · export actions are now available"); st.download_button("Download final MP4", st.session_state.final_video, file_name="aungmin-movie-recap.mp4", mime="video/mp4")
        elif st.session_state.preview_ready:
            st.warning("The renderer did not return a video file. Check the message above and try again.")
        else: st.markdown('<div class="previewbox"><div><div class="play">◌</div><strong>Preview locked</strong><br><span class="small">Complete processing to review before export.</span></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="small" style="margin-top:2.5rem">Use only media you own or have permission to process. Platform access and download behavior depends on provider rules and your configured source adapter.</div>', unsafe_allow_html=True)
