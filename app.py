import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from streamlit_app import (
    APP_NAME, EditorState, PLATFORMS, RATIOS, SourceInfo, VOICE_NAMES,
    create_voiceover, download_authorized_source, embed_preview_html,
    generate_recap_bundle, generate_recap_from_transcript, inspect_source, make_srt, preview_html,
    probe_duration, render_mp4, save_uploaded_file, duration_notice,
    validate_media_file, fetch_public_transcript, MAX_DURATION_SECONDS,
)

st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root{color-scheme:dark}
[data-testid="stAppViewContainer"]{background:radial-gradient(circle at 82% 0%,rgba(24,82,92,.42),transparent 32%),radial-gradient(circle at 10% 46%,rgba(63,24,100,.46),transparent 35%),#070a14}
[data-testid="stHeader"]{background:rgba(5,7,16,.72)}
.block-container{max-width:1540px;padding:.65rem clamp(.8rem,2.3vw,2.5rem) 1.4rem;overflow:visible}
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
@media(max-width:900px){.block-container{overflow:visible}.panel{padding:.8rem}.brandbar small{font-size:.56rem}.stage{height:260px}.empty-preview{height:260px}}
</style>
""", unsafe_allow_html=True)

if "source" not in st.session_state: st.session_state.source = None
if "media_path" not in st.session_state: st.session_state.media_path = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "bundle" not in st.session_state: st.session_state.bundle = None
if "transcript" not in st.session_state: st.session_state.transcript = None
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
            st.video(st.session_state.media_path, start_time=0)
        elif st.session_state.source and st.session_state.source.url.startswith(("http://", "https://")):
            embedded = embed_preview_html(st.session_state.source)
            if embedded:
                components.html(embedded, height=405, scrolling=False)
                st.caption("Preview ပြထားသော်လည်း provider download ခွင့်မပေးပါက recap အတွက် video file upload လုပ်ပါ။")
            else:
                st.markdown('<div class="empty-preview">ဒီ provider မှာ browser preview မရပါ။ Recap ဆက်လုပ်ရန် ကိုယ်ပိုင်/ခွင့်ပြုချက်ရ video file ကို upload လုပ်ပါ။</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-preview">Upload a video or load an authorized public link.</div>', unsafe_allow_html=True)
    with final_tab:
        st.markdown('<div class="stage-label"><span>Edited recap output</span><span>04 · FINISH</span></div>', unsafe_allow_html=True)
        if st.session_state.final_video:
            final_path = str(Path(tempfile.gettempdir()) / "aungmin-final-preview.mp4")
            Path(final_path).write_bytes(st.session_state.final_video)
            st.video(final_path, start_time=0)
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
        quality = st.selectbox("Download quality / အရည်အသွေး", ["MP4 720p", "MP4 480p", "MP4 360p"], index=0, key="download_quality") if mode == "Paste video link" else "MP4 720p"
        st.caption("Public/authorized media only. Link loading depends on provider access rules. Video limit: 5 minutes. Quality options depend on provider availability.")
        st.session_state.api_key = st.text_input("Google AI Studio API key", type="password", key="api_key_input", help="Session-only key. Never commit it to GitHub.")
        if st.button("Load original video", type="primary", use_container_width=True):
            try:
                st.session_state.transcript = None
                if mode == "Upload video":
                    if not uploaded: raise ValueError("Choose a video file first.")
                    candidate = save_uploaded_file(uploaded, "aungmin-uploaded-source")
                    duration = probe_duration(candidate)
                    validate_media_file(candidate, duration)
                    st.session_state.media_path = candidate
                    st.session_state.source = SourceInfo(f"upload://{uploaded.name}", "Upload", uploaded.name, uploaded.name)
                    st.info(duration_notice(duration))
                else:
                    source = inspect_source(source_url)
                    st.session_state.source = source
                    try:
                        with st.spinner("Loading the original source video…"):
                            candidate = download_authorized_source(source.url, quality)
                        duration = probe_duration(candidate)
                        validate_media_file(candidate, duration)
                        st.session_state.media_path = candidate
                        st.info(duration_notice(duration))
                    except ValueError as exc:
                        st.session_state.media_path = None
                        st.warning(f"Link preview ရနိုင်သော်လည်း video download မရပါ: {exc}")
                        if source.platform == "YouTube":
                            try:
                                with st.spinner("Public YouTube transcript ကို ရှာနေပါတယ်…"):
                                    st.session_state.transcript = fetch_public_transcript(source.url)
                                st.success("Public transcript ရပါပြီ။ Video file မ download လုပ်ဘဲ Quick Recap စနိုင်ပါပြီ။")
                            except ValueError as transcript_exc:
                                st.info(str(transcript_exc))
                st.session_state.final_video = None
                st.session_state.bundle = None
                if st.session_state.media_path:
                    st.success("Original video loaded. Preview is ready on the left.")
                else:
                    st.info("Link information loaded. Browser preview is available when the provider supports embedding; upload the file to create a recap.")
            except (ValueError, ImportError) as exc:
                st.error(str(exc))
    with tabs[1]:
        style = st.selectbox("Recap narration style / ဇာတ်ကြောင်းပြောဟန်", ["ရုပ်ရှင်ဆန်သော ဇာတ်ကြောင်းပြောဟန်", "စိတ်လှုပ်ရှားဖွယ် ဇာတ်ကြောင်းပြောဟန်", "တည်ငြိမ်ပြီး ရှင်းလင်းသောဟန်", "လျှို့ဝှက်ဆန်းကြယ်သောဟန်", "ဝမ်းနည်းနက်ရှိုင်းသောဟန်"], index=0, key="recap_style")
        detail = "Essential"
        st.markdown('<div class="section-note">Quick Recap သည် video file ရှိလျှင် visuals/audio ကို အသုံးပြုမည်။ YouTube download မရလျှင် public transcript ကို အသုံးပြုပြီး မြန်မာဇာတ်ကြောင်း၊ မြန်မာအသံနှင့် မြန်မာစာတန်းထိုးအတွက် ပြင်ဆင်မည်။</div>', unsafe_allow_html=True)
        if st.session_state.transcript:
            st.info("YouTube public transcript ready — video download မလိုဘဲ recap script ထုတ်နိုင်ပါပြီ။ Final MP4 အတွက်တော့ authorized video file upload လိုပါမယ်။")
        if st.button("Quick Recap စတင်မယ်", type="primary", use_container_width=True):
            if not st.session_state.source or (not st.session_state.media_path and not st.session_state.transcript):
                st.error("Load a video file or a YouTube link with public captions first.")
            elif not st.session_state.api_key:
                st.error("Enter your Google AI Studio API key in 01 · Source before generating.")
            else:
                with st.spinner("Analyzing video visuals/audio and writing Burmese recap…"):
                    try:
                        if st.session_state.media_path:
                            st.session_state.bundle = generate_recap_bundle(st.session_state.api_key, st.session_state.source, st.session_state.media_path, style, detail, editor.speed, editor.flip)
                        else:
                            st.session_state.bundle = generate_recap_from_transcript(st.session_state.api_key, st.session_state.transcript, style, detail)
                        st.success("မြန်မာ recap၊ မြန်မာ voice နှင့် မြန်မာ subtitle အတွက် ပြင်ဆင်ပြီးပါပြီ။")
                    except (ValueError, ImportError) as exc:
                        st.error(str(exc))
        if st.session_state.bundle:
            st.text_area("Editable Burmese recap", st.session_state.bundle["recap_bn"], height=170, key="editable_recap")
            st.caption("Edit this narration before rendering. Changes are applied to the voiceover and subtitle timing.")
    with tabs[2]:
        voice_labels = {"my-MM-NilarNeural": "အမျိုးသမီးအသံ — ကြည်လင်ပြီး တည်ငြိမ်သောဟန်", "my-MM-ThihaNeural": "အမျိုးသားအသံ — နက်ရှိုင်းပြီး ရုပ်ရှင်ဆန်သောဟန်", "en-US-AriaNeural": "အင်္ဂလိပ်အသံ — အရေးပေါ်အစားထိုးအသံ"}
        voice_name = st.selectbox("Voice profile / မြန်မာအသံပုံစံ", list(VOICE_NAMES), index=0, format_func=lambda name: voice_labels.get(name, name), key="voice_name")
        audio_speed = 1.0
        st.markdown('<div class="section-note">ရွေးထားသော မြန်မာအသံပုံစံဖြင့် narration ထုတ်မည်။ အသံနှင့် မြန်မာစာတန်းထိုးကို တစ်ကြိမ်တည်း render လုပ်မည်။</div>', unsafe_allow_html=True)
    with tabs[3]:
        st.markdown("**အလိုအလျောက်ပြင်ဆင်မှု** — မြန်မာ recap အတွက် ရိုးရှင်းသော output")
        editor.speed = 1.0
        editor.flip = False
        editor.blur_strength = 28 if st.checkbox("Blur ထည့်မယ်", value=editor.blur_strength > 0, key="blur_enabled") else 0
        editor.subtitle_mode = "Burmese only"
        editor.subtitle_position = "Bottom"
        editor.subtitle_size = 34
        editor.subtitle_offset = 0.0
        output_platform = st.selectbox("Output format", PLATFORMS, format_func=lambda item: f"{item} · {RATIOS[item]}", key="output_platform")
        st.info("Final output: 1920×1080 · 30 FPS · မူရင်း video ကြာချိန်အတိုင်း။ Source က 720p/480p ဖြစ်လျှင် 1080p သို့ upscale လုပ်မည်၊ မူရင်း detail အသစ်ဖန်တီးမည်မဟုတ်ပါ။")
        music_path = None
        st.markdown('<div class="section-note">Blur ကို privacy/editing အတွက်သာ အသုံးပြုမည်။ Final video တွင် မြန်မာ voice narration နှင့် မြန်မာ subtitle တစ်မျိုးတည်း ပါမည်။</div>', unsafe_allow_html=True)
        if st.button("Render final recap video", type="primary", use_container_width=True):
            if not st.session_state.bundle:
                st.error("Generate and review the Burmese recap first.")
            elif not st.session_state.media_path:
                st.error("Transcript recap script ရပါပြီ။ Final MP4 render အတွက် authorized video file ကို upload လုပ်ပါ။")
            else:
                with st.spinner("Rendering Burmese voiceover, subtitles, effects, and 1080p/30fps MP4 preview…"):
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
