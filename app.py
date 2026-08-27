import base64
import tempfile
from pathlib import Path
import time

import streamlit as st
import streamlit.components.v1 as components

from streamlit_app import (
    APP_NAME, EditorState, FONT_FAMILIES, FONT_FILES, FONT_PRESETS, PLATFORMS, RATIOS, SourceInfo, VOICE_NAMES,
    create_voiceover, fit_audio_to_duration, pad_or_trim_audio_to_duration, download_authorized_source, embed_preview_html,
    generate_recap_bundle, generate_recap_from_transcript, inspect_source, make_srt, preview_html,
    probe_duration, render_mp4, render_bundle_to_mp4, render_voice_preview, save_uploaded_file, duration_notice,
    validate_media_file, fetch_public_transcript, MAX_DURATION_SECONDS,
)
from streamlit_app.audio import caption_for_time
from streamlit_app.pipeline import run_one_click_recap
from streamlit_app.editor import add_preview_subtitle, extract_preview_frame, sync_blur_from_canvas, sync_overlays_from_canvas, canvas_initial_drawing

st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root{color-scheme:dark}
[data-testid="stAppViewContainer"]{background:radial-gradient(circle at 88% 0%,rgba(116,18,35,.22),transparent 30%),radial-gradient(circle at 8% 48%,rgba(40,24,72,.46),transparent 38%),#08090d}
[data-testid="stHeader"]{background:rgba(5,6,10,.88)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#111318,#090a0e);border-right:1px solid rgba(255,255,255,.12)}
.block-container{max-width:1540px;padding:.65rem clamp(.8rem,2.3vw,2.5rem) 1.4rem;overflow:visible}
.brandbar{height:52px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.13);color:#f4f6ff;font-weight:800;letter-spacing:-.03em}
.brandbar small{color:#f05a67;font-size:.64rem;letter-spacing:.16em;text-transform:uppercase}
.brandbar .trial{display:inline-flex;align-items:center;gap:.35rem;color:#ff6974;background:rgba(224,47,65,.12);border:1px solid rgba(240,90,103,.38);padding:.28rem .52rem;border-radius:999px;font-size:.62rem;letter-spacing:.12em}
.workspace{padding-top:.7rem}
.panel{background:linear-gradient(145deg,rgba(19,22,29,.97),rgba(10,11,16,.98));border:1px solid rgba(255,255,255,.14);border-radius:14px;padding:1rem;box-shadow:0 18px 55px rgba(0,0,0,.3)}
.panel-head{display:flex;align-items:center;justify-content:space-between;gap:1rem;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:.75rem;margin-bottom:.8rem}.panel-head:after{content:'';display:block}
.panel-title{color:#f2f4ff;font-size:.68rem;letter-spacing:.18em;text-transform:uppercase;font-weight:850}
.ready{color:#76eadb;font-size:.75rem;white-space:nowrap}
.info{color:#adb6cc;font-size:.76rem;line-height:1.45}
.stage-label{display:flex;align-items:center;justify-content:space-between;color:#dce1ef;font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;font-weight:800;margin:.7rem 0 .45rem}
.section-note{color:#9da7be;font-size:.74rem;line-height:1.42;margin:.35rem 0 .7rem}
div[data-testid="stTextInput"] label,div[data-testid="stSelectbox"] label,div[data-testid="stTextArea"] label,div[data-testid="stSlider"] label,div[data-testid="stFileUploader"] label,div[data-testid="stRadio"] label{color:#e7eaf4!important;font-weight:700!important}
div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea,div[data-baseweb="select"]>div{background:#f4f5f9!important;color:#101422!important;border:0!important;border-radius:10px!important}
div[data-testid="stButton"]>button{min-height:2.45rem;border-radius:10px;background:#17213b;color:#f7f8ff;border:1px solid rgba(255,255,255,.2);font-weight:750}
div[data-testid="stButton"]>button[kind="primary"],button[kind="primaryFormSubmit"]{background:linear-gradient(105deg,#e23d52,#ff6b61);color:#fff;border:0;box-shadow:0 10px 26px rgba(226,61,82,.2)}
[data-testid="stTabs"] [role="tablist"]{gap:.25rem;border-bottom:1px solid rgba(255,255,255,.1)}
[data-testid="stTabs"] button{color:#98a2ba!important;font-weight:800!important;font-size:.72rem!important;border-radius:8px 8px 0 0;padding:.55rem .7rem}
[data-testid="stTabs"] button:hover{color:#ff9aa1!important;background:rgba(226,61,82,.08)}
[data-testid="stTabs"] button[aria-selected="true"]{color:#ff6672!important;border-bottom-color:#e23d52!important}
[data-testid="stAlert"]{color:#edf0f8}
@media(max-width:900px){.block-container{overflow:visible}.panel{padding:.8rem}.brandbar small{font-size:.56rem}.stage{height:260px}.empty-preview{height:260px}}
</style>
""", unsafe_allow_html=True)

# Streamlit widgets use the browser's font by default. Embed a known Unicode
# Burmese font so labels and controls do not fall back to broken glyphs.
_ui_font = Path(__file__).resolve().parent / "fonts" / "Pyidaungsu-Book-Regular.ttf"
if _ui_font.is_file():
    _ui_font_b64 = base64.b64encode(_ui_font.read_bytes()).decode("ascii")
    st.markdown(f"<style>@font-face{{font-family:'AungMinMyanmar';src:url(data:font/ttf;base64,{_ui_font_b64}) format('truetype');font-weight:400;font-style:normal}}body,[data-testid='stAppViewContainer'],button,input,textarea,[role='option'],label,p,small,div{{font-family:'AungMinMyanmar','Pyidaungsu Book',sans-serif!important}}</style>", unsafe_allow_html=True)

if "source" not in st.session_state: st.session_state.source = None
if "media_path" not in st.session_state: st.session_state.media_path = None
if "api_key" not in st.session_state: st.session_state.api_key = ""
if "bundle" not in st.session_state: st.session_state.bundle = None
if "transcript" not in st.session_state: st.session_state.transcript = None
if "final_video" not in st.session_state: st.session_state.final_video = None
if "voice_preview" not in st.session_state: st.session_state.voice_preview = None
if "script_approved" not in st.session_state: st.session_state.script_approved = False
if "voice_approved" not in st.session_state: st.session_state.voice_approved = False
if "editor" not in st.session_state: st.session_state.editor = EditorState()
editor = st.session_state.editor

with st.sidebar:
    st.markdown('<div style="font-weight:900;font-size:1.05rem;color:#fff">◈ AungMin Movie Recap</div><div style="color:#f05a67;font-size:.62rem;letter-spacing:.14em;margin:.25rem 0 1.15rem">AI VIDEO STUDIO</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#ff6672;font-size:.68rem;letter-spacing:.14em;font-weight:800;margin-bottom:.45rem">WORKSPACE</div>', unsafe_allow_html=True)
    st.markdown('<div style="padding:.6rem .7rem;border-radius:9px;background:rgba(226,61,82,.16);color:#fff;font-weight:750">▣ Studio</div><div style="padding:.6rem .7rem;color:#a7adbd">▤ Transcript Hub</div><div style="padding:.6rem .7rem;color:#a7adbd">⇩ Downloads</div><div style="padding:.6rem .7rem;color:#a7adbd">◯ Profile</div><div style="padding:.6rem .7rem;color:#a7adbd">? Support</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:1px;background:rgba(255,255,255,.12);margin:1rem 0"></div><div style="color:#858c9e;font-size:.72rem;line-height:1.5">Current app features remain available in the Studio workspace. Authorized media only.</div>', unsafe_allow_html=True)

st.markdown('<div class="brandbar"><div>◈ &nbsp;AungMin Movie Recap</div><div style="display:flex;align-items:center;gap:.65rem"><span class="trial">● FREE STUDIO</span><small>AI VIDEO WORKSPACE</small></div></div>', unsafe_allow_html=True)

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
        live_preview_slot = None
        if not st.session_state.final_video and st.session_state.media_path:
            # Keep one stable host in the Final recap tab. The Finish controls
            # populate this same container later instead of replacing it on rerun.
            live_preview_slot = st.container()
        if st.session_state.final_video:
            final_path = str(Path(tempfile.gettempdir()) / "aungmin-final-preview.mp4")
            Path(final_path).write_bytes(st.session_state.final_video)
            st.video(final_path, start_time=0)
            st.download_button("Download final MP4", st.session_state.final_video, file_name="aungmin-movie-recap.mp4", mime="video/mp4", use_container_width=True)
        else:
            if st.session_state.media_path and st.session_state.bundle and st.session_state.voice_approved:
                st.markdown('<div class="section-note" style="margin:.65rem 0 .45rem">Finish preview ကိုစစ်ပြီး အောက်ကခလုတ်ကိုနှိပ်မှ Final MP4 render စတင်ပါမယ်။</div>', unsafe_allow_html=True)
                if st.button("▶ Render final recap video", type="primary", use_container_width=True, key="render_final_top"):
                    st.session_state.render_requested = True
                    st.rerun()
            else:
                st.markdown('<div class="empty-preview">02 Script ကို approve လုပ်ပြီး 03 Recap Voice ကို approve လုပ်ပါ။ ထို့နောက် Finish preview နှင့် Final render ကို အသုံးပြုနိုင်ပါမယ်။</div>', unsafe_allow_html=True)
    if st.session_state.source:
        duration = probe_duration(st.session_state.media_path) if st.session_state.media_path else 0
        st.markdown(f'<div class="info" style="margin-top:.7rem">Loaded: <b>{st.session_state.source.platform}</b> · {st.session_state.source.name} · {duration:.1f}s · Original source remains available for comparison.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="workspace panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-head"><div class="panel-title">Production control room</div><div class="ready">● 01–04 selectable</div></div>', unsafe_allow_html=True)
    st.markdown('<div style="margin:.8rem 0;padding:.8rem;border:1px solid rgba(255,102,114,.42);border-radius:12px;background:linear-gradient(105deg,rgba(226,61,82,.18),rgba(255,107,97,.08))"><b style="color:#ff9aa1">One-click Recap</b><br><span style="color:#c5cada;font-size:.78rem">Source video ကို analysis လုပ်ပြီး full recap script၊ Burmese voice၊ Burmese/English subtitle၊ auto blur နဲ့ final MP4 ကို အလိုအလျောက်လုပ်ပါမယ်။ ပြီးမှ manual controls နဲ့ ထပ်ပြင်နိုင်ပါတယ်။</span></div>', unsafe_allow_html=True)
    if st.button("🎬 Recap တစ်ချက်နှိပ်ပြီး အလိုအလျောက်လုပ်မယ်", type="primary", use_container_width=True, key="one_click_recap"):
        if not st.session_state.media_path:
            st.error("01 · Source မှာ video file ကို အရင် Load လုပ်ပါ။")
        elif not st.session_state.api_key:
            st.error("Google AI Studio API key ထည့်ပြီးမှ One-click Recap ကို စတင်နိုင်ပါမယ်။")
        else:
            one_click_progress = st.progress(0, text="One-click Recap ပြင်ဆင်နေသည်…")
            one_click_timing = st.empty()
            one_click_started = time.monotonic()
            try:
                def update_one_click(percent: int, message: str, pipeline_started: float) -> None:
                    one_click_progress.progress(min(98, max(5, percent)), text=f"{message}…")
                    one_click_timing.caption(f"ကြာချိန်: {time.monotonic() - one_click_started:.0f} စက္ကန့်")
                one_click_progress.progress(8, text="Scene အားလုံးကို analysis လုပ်နေသည်…")
                bundle, voice_preview, final_video = run_one_click_recap(
                    st.session_state.api_key,
                    st.session_state.source,
                    st.session_state.media_path,
                    editor,
                    output_platform="TikTok",
                    voice_name="my-MM-ThihaNeural",
                    style="စိတ်လှုပ်ရှားဖွယ် ဇာတ်ကြောင်းရေးဟန်",
                    detail="Detailed",
                    progress=update_one_click,
                )
                st.session_state.bundle = bundle
                st.session_state.script_approved = True
                st.session_state.voice_preview = voice_preview
                st.session_state.voice_approved = True
                st.session_state.final_video = final_video
                one_click_progress.progress(100, text="One-click Final MP4 အဆင်သင့်ဖြစ်ပါပြီ")
                one_click_timing.caption(f"စုစုပေါင်းကြာချိန်: {time.monotonic() - one_click_started:.0f} စက္ကန့်")
                st.success("One-click Recap ပြီးပါပြီ။ Final tab မှာ result ကိုကြည့်ပြီး လိုအပ်ရင် manual controls နဲ့ ပြင်နိုင်ပါတယ်။")
                st.rerun()
            except (ValueError, ImportError, OSError) as exc:
                one_click_progress.empty()
                one_click_timing.empty()
                st.error(f"One-click Recap မအောင်မြင်ပါ: {exc}")
    tabs = st.tabs(["01 · Source", "02 · Voice script", "03 · Recap voice", "04 · Finish"])
    with tabs[0]:
        mode = st.radio("Input type", ["Upload video", "Paste video link"], horizontal=True, key="input_mode")
        uploaded = st.file_uploader("Upload video file", type=["mp4", "mov", "webm", "mkv"], key="source_upload") if mode == "Upload video" else None
        source_url = st.text_input("Video link", placeholder="YouTube · TikTok · Bilibili · RedNote · public URL", key="source_url") if mode == "Paste video link" else ""
        quality = st.selectbox("Download quality / အရည်အသွေး", ["MP4 720p", "MP4 480p", "MP4 360p"], index=0, key="download_quality") if mode == "Paste video link" else "MP4 720p"
        st.caption("Public/authorized media only. Link loading depends on provider access rules. Video limit: 5 minutes. Quality options depend on provider availability.")
        st.markdown('<div style="margin:.55rem 0 .35rem;padding:.7rem .8rem;border:1px solid rgba(112,232,216,.3);border-radius:12px;background:rgba(112,232,216,.08)"><b style="color:#75eadb">Gemini API key လိုပါသလား?</b><br><span style="color:#b9c4d8;font-size:.78rem">Google AI Studio မှာ key ယူပြီး ဒီအောက်က box ထဲ session-only ထည့်ပါ။</span><br><a href="https://aistudio.google.com/app/apikey" target="_blank" style="display:inline-block;margin-top:.45rem;color:#07101b;background:#75eadb;padding:.42rem .7rem;border-radius:8px;text-decoration:none;font-weight:800;font-size:.78rem">API key ရယူရန် → Google AI Studio</a></div>', unsafe_allow_html=True)
        st.session_state.api_key = st.text_input("Google AI Studio API key", type="password", key="api_key_input", help="Session-only key. Never commit it to GitHub.")
        if st.button("စတင်ရန် · Load original video", type="primary", use_container_width=True):
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
                    except (ValueError, TypeError) as exc:
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
                st.session_state.voice_preview = None
                st.session_state.script_approved = False
                st.session_state.voice_approved = False
                if st.session_state.media_path:
                    st.success("Original video loaded. Studio preview is ready.")
                else:
                    st.info("Link information loaded. Browser preview is available when the provider supports embedding; upload the file to create a recap.")
            except (ValueError, ImportError) as exc:
                st.error(str(exc))
    with tabs[1]:
        style = st.selectbox("Recap script style / ဇာတ်ကြောင်းရေးဟန်", ["ရုပ်ရှင်ဆန်သော ဇာတ်ကြောင်းရေးဟန်", "စိတ်လှုပ်ရှားဖွယ် ဇာတ်ကြောင်းရေးဟန်", "တည်ငြိမ်ပြီး ရှင်းလင်းသောဟန်", "လျှို့ဝှက်ဆန်းကြယ်သောဟန်", "ဝမ်းနည်းနက်ရှိုင်းသောဟန်"], index=0, key="recap_style")
        detail = "Essential"
        st.markdown('<div class="section-note">ဒီအဆင့်မှာ ဘာသာပြန်ထားတဲ့ Burmese recap script စာသားပဲ ထုတ်ပါမယ်။ Voice နဲ့ MP4 ကို No.3 မှာပဲ ထုတ်ပါမယ်။ စာမူကိုဖတ်ပြီး ကြိုက်မှ Approve လုပ်ပါ။</div>', unsafe_allow_html=True)
        if st.button("Burmese recap script ထုတ်မယ်", type="primary", use_container_width=True):
            if not st.session_state.media_path and not st.session_state.transcript:
                st.error("01 · Source မှာ video upload သို့မဟုတ် public transcript ရအောင် အရင်လုပ်ပါ။")
            elif not st.session_state.api_key:
                st.error("01 · Source ထဲမှာ Google AI Studio API key ထည့်ပြီးမှ စတင်ပါ။")
            else:
                progress = st.progress(0, text="Script ထုတ်ရန် ပြင်ဆင်နေသည်…")
                timing = st.empty()
                started = time.monotonic()
                try:
                    def update_script_progress(percent: int, message: str, pipeline_started: float) -> None:
                        progress.progress(min(95, max(8, percent)), text=f"{message}…")
                        timing.caption(f"ကြာချိန်: {time.monotonic() - started:.0f} စက္ကန့်")
                    if st.session_state.media_path:
                        bundle = generate_recap_bundle(st.session_state.api_key, st.session_state.source, st.session_state.media_path, style, detail, 1.0, False, update_script_progress)
                    else:
                        bundle = generate_recap_from_transcript(st.session_state.api_key, st.session_state.transcript, style, detail)
                    st.session_state.bundle = bundle
                    st.session_state.script_approved = False
                    st.session_state.voice_preview = None
                    progress.progress(100, text="Burmese recap script အဆင်သင့်ဖြစ်ပါပြီ")
                    timing.caption(f"စုစုပေါင်းကြာချိန်: {time.monotonic() - started:.0f} စက္ကန့်")
                except (ValueError, ImportError, OSError) as exc:
                    progress.empty()
                    timing.empty()
                    st.error(f"Script မထုတ်နိုင်ပါ: {exc}")
        if st.session_state.bundle:
            edited_script = st.text_area("Burmese recap script / ပြင်ဆင်ရန်", st.session_state.bundle["recap_bn"], height=220, key="editable_recap")
            if st.button("ဒီ script ကို အတည်ပြုပြီး No.3 Voice သို့ ဆက်မယ်", type="primary", use_container_width=True):
                st.session_state.bundle["recap_bn"] = edited_script.strip()
                st.session_state.bundle["subtitle_bn"] = edited_script.strip()
                st.session_state.script_approved = bool(edited_script.strip())
                if st.session_state.script_approved:
                    st.success("Script အတည်ပြုပြီးပါပြီ။ No.3 · Voice ကိုဖွင့်ပြီး narration ထုတ်ပါ။")
                else:
                    st.error("Script အလွတ်မဖြစ်ရပါ။")
            if st.session_state.script_approved:
                st.success("Script approved — No.3 Voice မှာ အသံ preview ထုတ်နိုင်ပါပြီ။")
    with tabs[2]:
        voice_labels = {"my-MM-NilarNeural": "အမျိုးသမီးအသံ — ကြည်လင်ပြီး တည်ငြိမ်သောဟန်", "my-MM-ThihaNeural": "အမျိုးသားအသံ — နက်ရှိုင်းပြီး ရုပ်ရှင်ဆန်သောဟန်", "en-US-AriaNeural": "အင်္ဂလိပ်အသံ — အရေးပေါ်အစားထိုးအသံ"}
        voice_name = st.selectbox("Voice profile / မြန်မာအသံပုံစံ", list(VOICE_NAMES), index=1, format_func=lambda name: voice_labels.get(name, name), key="voice_name")
        st.markdown('<div class="section-note">No.2 မှာ အတည်ပြုထားတဲ့ script ကိုပဲ အသံပြောင်းပါမယ်။ မူရင်း video အသံကို ဖျက်ပြီး Burmese recap narration တစ်ခုတည်းနဲ့ preview ထုတ်ပါမယ်။</div>', unsafe_allow_html=True)
        if st.button("Burmese recap voice preview ထုတ်မယ်", type="primary", use_container_width=True):
            if not st.session_state.bundle or not st.session_state.script_approved:
                st.error("02 · Recap မှာ script ကို အရင် Generate လုပ်ပြီး Approve လုပ်ပါ။")
            elif not st.session_state.media_path:
                st.error("03 · Voice preview အတွက် original video file လိုပါမယ်။")
            else:
                progress = st.progress(0, text="Voice preview ပြင်ဆင်နေသည်…")
                timing = st.empty()
                started = time.monotonic()
                try:
                    def update_voice_progress(percent: int, message: str, pipeline_started: float) -> None:
                        progress.progress(min(99, max(8, percent)), text=f"{message}…")
                        timing.caption(f"ကြာချိန်: {time.monotonic() - started:.0f} စက္ကန့်")
                    voice_preview = render_voice_preview(st.session_state.media_path, st.session_state.bundle, voice_name, editor, st.session_state.get("output_platform", "YouTube"), update_voice_progress)
                    st.session_state.voice_preview = voice_preview
                    st.session_state.voice_approved = False
                    progress.progress(100, text="Voice preview အဆင်သင့်ဖြစ်ပါပြီ")
                    timing.caption(f"စုစုပေါင်းကြာချိန်: {time.monotonic() - started:.0f} စက္ကန့်")
                except (ValueError, ImportError, OSError) as exc:
                    progress.empty()
                    timing.empty()
                    st.error(f"Voice preview မထုတ်နိုင်ပါ: {exc}")
        if st.session_state.voice_preview:
            st.audio(st.session_state.voice_preview["voice_path"])
            voice_preview_path = Path(tempfile.gettempdir()) / "aungmin-approved-voice-preview.mp4"
            voice_preview_path.write_bytes(st.session_state.voice_preview["video_bytes"])
            st.video(str(voice_preview_path), start_time=0)
            st.caption(f"Voice duration: {st.session_state.voice_preview['voice_duration']:.1f}s · မူရင်းအသံကို ဖယ်ထားသည်။")
            if st.button("ဒီ Burmese voice ကို အတည်ပြုပြီး No.4 Finish သို့ ဆက်မယ်", type="primary", use_container_width=True):
                st.session_state.voice_approved = True
            if st.session_state.get("voice_approved"):
                st.success("Voice approved — No.4 Finish မှာ blur၊ subtitle၊ font၊ size၊ position နဲ့ logo ကို ချိန်နိုင်ပါပြီ။")
    with tabs[3]:
        st.markdown("**No.3 approved recap ကို အဆုံးသတ်ပြင်ဆင်ရန်**")
        st.markdown('<div class="section-note">ဒီနေရာမှာ No.3 မှာ approve လုပ်ထားတဲ့ Burmese voice + video ကိုပဲ သုံးပါမယ်။ မူရင်းအသံကို ပြန်မထည့်ပါ။ Blur၊ manual subtitle၊ font၊ size၊ position နဲ့ logo ကို preview ကြည့်ပြီး ပြင်ပါမယ်။</div>', unsafe_allow_html=True)
        with st.expander("Text & Branding / စာတန်းနှင့် အမှတ်တံဆိပ်", expanded=True):
            selected_font = st.selectbox("Subtitle font / မြန်မာစာတန်းဖောင့်", FONT_PRESETS, index=FONT_PRESETS.index("Noto Sans Myanmar Regular") if "Noto Sans Myanmar Regular" in FONT_PRESETS else 3, key="subtitle_font")
            editor.subtitle_font = selected_font
            logo_upload = st.file_uploader("Logo upload / လိုဂိုထည့်ရန် (optional)", type=["png", "jpg", "jpeg"], key="logo_upload")
            if logo_upload:
                st.session_state.logo_path = save_uploaded_file(logo_upload, "aungmin-logo")
            if "logo_path" not in st.session_state:
                st.session_state.logo_path = None
            editor.logo_position = st.selectbox("Logo position / လိုဂိုနေရာ", ["Top Right", "Top Left", "Bottom Right", "Bottom Left"], index=0, key="logo_position")
            editor.logo_motion = st.selectbox("Logo motion / လိုဂိုလှုပ်ရှားပုံ", ["Static", "Slow drift"], index=1, key="logo_motion")
            manual_subtitle = st.text_area("Manual Burmese subtitle / ကိုယ်တိုင်ထည့်မည့် စာတန်း", value=st.session_state.get("manual_subtitle", ""), height=100, key="manual_subtitle")
            watermark_text = st.text_input("Watermark text / ရေစာစာသား (optional)", value=st.session_state.get("watermark_text", ""), key="watermark_text")
            editor.watermark_text = watermark_text
        st.caption("Auto subtitle မမှန်ရင် ဒီနေရာမှာ ပြင်နိုင်ပါတယ်။ စာတန်း၊ logo နဲ့ watermark ကို video preview ပေါ်မှာ ချက်ချင်းမြင်ပြီး ရွှေ့နိုင်ပါမယ်။")
        editor.speed = 1.0
        editor.flip = False
        with st.expander("Blur / မူရင်းစာတန်းဖုံးရန်", expanded=True):
            blur_enabled = st.checkbox("Blur အဖွင့် / အပိတ်", value=editor.blur_enabled or editor.blur_strength > 0, key="blur_enabled")
            editor.blur_enabled = blur_enabled
            blur_mode = st.selectbox("Blur mode / အုပ်မည့်နည်း", ["Auto default (အောက်ခြေစာတန်း)", "Manual drag (video ပေါ်ရွှေ့ရန်)"], index=0, key="blur_mode", disabled=not blur_enabled)
            editor.blur_strength = st.slider("Blur strength / အုပ်အား", 0, 60, 28, 2, disabled=not blur_enabled) if blur_enabled else 0
            if blur_enabled and blur_mode.startswith("Auto"):
                # Cover the full lower subtitle band with a small safety margin.
                editor.blur_x, editor.blur_y, editor.blur_w, editor.blur_h = 0, 68, 100, 32
            if blur_enabled and blur_mode.startswith("Manual"):
                st.caption("Auto default က အောက်ခြေစာတန်းဧရိယာကို အုပ်ပါသည်။ မတူသောနေရာဖြစ်လျှင် x/y/width/height ကို manual ပြင်ပါ။")
                editor.blur_x = st.slider("Blur X %", 0, 95, editor.blur_x, 1)
                editor.blur_y = st.slider("Blur Y %", 0, 95, editor.blur_y, 1)
                editor.blur_w = st.slider("Blur width %", 5, 100, editor.blur_w, 1)
            editor.blur_h = st.slider("Blur height %", 5, 80, editor.blur_h, 1)
        with st.expander("Subtitle / စာတန်းထိုး", expanded=True):
            editor.subtitle_mode = st.selectbox("Subtitle language / စာတန်းဘာသာ", ["Burmese + English", "Burmese only", "English only"], index=0, key="subtitle_mode")
            if st.button("Auto Subtitle · အသံနဲ့ 100% ချိန်ညှိ", type="secondary", use_container_width=True):
                editor.subtitle_auto_sync = True
                st.session_state.auto_subtitle_ready = True
                st.success("Auto Subtitle ဖွင့်ပြီးပါပြီ။ Approved voice ကြာချိန်အတိုင်း စာတန်းကို အလိုအလျောက်ခွဲပါမယ်။")
            st.caption("Auto Subtitle က narration duration အတိုင်း caption timing ချိန်ပြီး 9:16 / 16:9 output canvas အတိုင်း ပြပါမယ်။")
            subtitle_enabled = st.checkbox("Subtitle အဖွင့် / အပိတ်", value=editor.subtitle_enabled, key="subtitle_enabled")
            editor.subtitle_enabled = subtitle_enabled
            editor.subtitle_position = st.selectbox("Subtitle position / စာတန်းနေရာ", ["Bottom", "Center", "Top"], index=0, key="subtitle_position")
            editor.subtitle_size = st.slider("Subtitle size / စာလုံးအရွယ်", 24, 64, 42, 2, key="subtitle_size")
            editor.subtitle_design = st.selectbox("Subtitle design / စာတန်းဒီဇိုင်း", ["Yellow + black outline", "White + black outline", "Cyan + black outline", "White + dark box", "Custom color"], key="subtitle_design")
            design_map = {
                "Yellow + black outline": ("#FFF200", "#000000", "#000000", 0),
                "White + black outline": ("#FFFFFF", "#000000", "#000000", 0),
                "Cyan + black outline": ("#63F5FF", "#000000", "#000000", 0),
                "White + dark box": ("#FFFFFF", "#000000", "#000000", 72),
            }
            if editor.subtitle_design == "Custom color":
                editor.subtitle_fill = st.color_picker("Text color / စာသားအရောင်", editor.subtitle_fill, key="subtitle_fill")
                editor.subtitle_outline = st.color_picker("Outline color / အနားသတ်အရောင်", editor.subtitle_outline, key="subtitle_outline")
                editor.subtitle_background_opacity = st.slider("Background opacity", 0, 90, editor.subtitle_background_opacity, 5, key="subtitle_background_opacity")
            else:
                editor.subtitle_fill, editor.subtitle_outline, editor.subtitle_background, editor.subtitle_background_opacity = design_map[editor.subtitle_design]
            editor.subtitle_font = st.session_state.get("subtitle_font", "Pyidaungsu Book Regular")
            editor.subtitle_offset = 0.0
        with st.expander("Preview & Export / ကြိုတင်ကြည့်ပြီး ထုတ်ရန်", expanded=True):
            output_platform = st.selectbox("Output format", PLATFORMS, format_func=lambda item: f"{item} · {RATIOS[item]}", key="output_platform")
            output_dimensions = {"16:9": "1920×1080", "9:16": "1080×1920", "1:1": "1080×1080", "3:4": "1080×1440"}.get(RATIOS[output_platform], "1920×1080")
            if st.session_state.media_path:
                st.markdown("**Blur / subtitle / logo / watermark ကို video frame ပေါ်မှာ တိုက်ရိုက်ရွှေ့ပြီး ချိန်ပါ**")
                try:
                    from streamlit_drawable_canvas import st_canvas
                    source_duration = max(0.1, float(probe_duration(st.session_state.media_path)))
                    preview_time = st.slider("Preview scene / လက်ရှိကြည့်မည့်အချိန်", 0.0, source_duration, min(float(st.session_state.get("preview_time", 0.0)), source_duration), 0.1, key="preview_time")
                    ratio = RATIOS[output_platform]
                    canvas_width, canvas_height = ((405, 720) if ratio == "9:16" else (720, 405) if ratio == "16:9" else (540, 540))
                    frame = extract_preview_frame(st.session_state.media_path, width=canvas_width, height=canvas_height, timestamp=preview_time)
                    preview_bundle = dict(st.session_state.bundle or {})
                    manual_text = st.session_state.get("manual_subtitle", "").strip()
                    if manual_text:
                        preview_bundle["subtitle_bn"] = manual_text
                    max_preview_chars = 22 if ratio == "9:16" else 34 if ratio == "16:9" else 28
                    preview_text = caption_for_time(preview_bundle, preview_time, source_duration, editor.subtitle_mode, max_preview_chars) if preview_bundle else ""
                    logo_path = st.session_state.get("logo_path")
                    # Keep the canvas identity stable while dragging. Coordinates belong to
                    # the drawable state, not the widget key; including them remounted the
                    # component after every pointer event and made the preview disappear.
                    canvas_key = f"finish_overlay_canvas_{ratio}_{canvas_width}x{canvas_height}_{round(preview_time, 1)}_{editor.subtitle_font}_{editor.subtitle_size}_{editor.subtitle_fill}_{editor.subtitle_design}_{editor.subtitle_enabled}_{hash(preview_text) % 100000}_{hash(watermark_text) % 100000}_{editor.blur_enabled}_{editor.blur_strength}"
                    canvas_kwargs = dict(
                        fill_color="rgba(0, 0, 0, 0.58)", stroke_width=3, stroke_color="#70e8d8",
                        background_image=frame, update_streamlit=True, height=canvas_height, width=canvas_width,
                        drawing_mode="transform", initial_drawing=canvas_initial_drawing(editor, canvas_width, canvas_height, preview_text if editor.subtitle_enabled else "", FONT_FAMILIES.get(editor.subtitle_font, "Pyidaungsu Book"), logo_path),
                        display_toolbar=True, key=canvas_key,
                    )
                    preview_host = live_preview_slot if live_preview_slot is not None else st.container()
                    with preview_host:
                        st.markdown(f'<div class="stage-label"><span>Live final-output preview · {ratio}</span><span>{canvas_width}×{canvas_height}</span></div>', unsafe_allow_html=True)
                        if ratio == "9:16":
                            preview_columns = st.columns([1, 1, 1])
                            with preview_columns[1]:
                                canvas_result = st_canvas(**canvas_kwargs)
                        else:
                            canvas_result = st_canvas(**canvas_kwargs)
                    editor, coords = sync_blur_from_canvas(editor, canvas_result.json_data, canvas_width, canvas_height)
                    editor = sync_overlays_from_canvas(editor, canvas_result.json_data, canvas_width, canvas_height)
                    if coords:
                        st.caption(f"လက်ရှိ Blur: X {coords[0]}% · Y {coords[1]}% · Width {coords[2]}% · Height {coords[3]}% — box ကို video ပေါ်မှာ ဖိဆွဲရွှေ့ပါ။")
                    st.caption(f"Subtitle: X {editor.subtitle_x}% · Y {editor.subtitle_y}% · Size {editor.subtitle_size}px · Logo: X {editor.logo_x}% · Y {editor.logo_y}% · Watermark: X {editor.watermark_x}% · Y {editor.watermark_y}%")
                except ImportError:
                    st.warning("Direct canvas editor package မတက်သေးပါ။")
                except Exception as exc:
                    st.warning(f"Live preview editor မတက်နိုင်သေးပါ: {exc}")
            st.info(f"Final output: {output_dimensions} · 30 FPS · မူရင်း video ကြာချိန်အတိုင်း။ Source က resolution နိမ့်လျှင် upscale လုပ်မည်၊ မူရင်း detail အသစ်ဖန်တီးမည်မဟုတ်ပါ။")
            music_path = None
            st.markdown('<div class="section-note">Blur ကို privacy/editing အတွက်သာ အသုံးပြုမည်။ Final video တွင် မြန်မာ voice narration နှင့် မြန်မာ subtitle တစ်မျိုးတည်း ပါမည်။</div>', unsafe_allow_html=True)
            render_requested = bool(st.session_state.pop("render_requested", False))
            if st.button("Render final recap video", type="primary", use_container_width=True, key="render_final_controls") or render_requested:
                if not st.session_state.bundle or not st.session_state.script_approved:
                    st.error("02 · Recap မှာ script ကို အရင် Generate လုပ်ပြီး Approve လုပ်ပါ။")
                elif not st.session_state.voice_preview or not st.session_state.voice_approved:
                    st.error("03 · Voice မှာ Burmese recap voice ကို အရင်ထုတ်ပြီး Approve လုပ်ပါ။")
                elif not st.session_state.media_path:
                    st.error("Transcript recap script ရပါပြီ။ Final MP4 render အတွက် authorized video file ကို upload လုပ်ပါ။")
                else:
                    st.session_state.final_video = None
                    render_progress = st.progress(0, text="Final recap render ပြင်ဆင်နေသည်…")
                    render_timing = st.empty()
                    render_started = time.monotonic()
                    try:
                        approved_voice_path = st.session_state.voice_preview.get("voice_path") if st.session_state.voice_preview else None
                        approved_voice_bytes = st.session_state.voice_preview.get("voice_bytes") if st.session_state.voice_preview else None
                        approved_voice_file = Path(tempfile.gettempdir()) / "aungmin-approved-voice-for-finish.mp3"
                        if isinstance(approved_voice_bytes, (bytes, bytearray)) and len(approved_voice_bytes) > 128:
                            approved_voice_file.write_bytes(bytes(approved_voice_bytes))
                        elif approved_voice_path and Path(approved_voice_path).is_file():
                            approved_voice_file.write_bytes(Path(approved_voice_path).read_bytes())
                        else:
                            raise ValueError("No.3 မှာ approve လုပ်ထားသော voice ဖိုင်ကို မတွေ့ပါ။ Voice preview ကို ပြန်ထုတ်ပြီး approve လုပ်ပါ။")

                        render_bundle = dict(st.session_state.bundle)
                        manual_text = st.session_state.get("manual_subtitle", "").strip()
                        if manual_text:
                            render_bundle["subtitle_bn"] = manual_text

                        def update_render_progress(percent: int, message: str, pipeline_started: float) -> None:
                            render_progress.progress(min(99, max(5, percent)), text=f"{message}…")
                            render_timing.caption(f"ကြာချိန်: {time.monotonic() - render_started:.0f} စက္ကန့်")

                        final_bytes = render_bundle_to_mp4(
                            st.session_state.media_path,
                            render_bundle,
                            voice_name,
                            editor,
                            output_platform,
                            progress=update_render_progress,
                            logo_path=st.session_state.get("logo_path"),
                            approved_voice_path=str(approved_voice_file),
                        )
                        st.session_state.final_video = final_bytes
                        render_progress.progress(100, text="Final MP4 အဆင်သင့်ဖြစ်ပါပြီ")
                        render_timing.caption(f"စုစုပေါင်းကြာချိန်: {time.monotonic() - render_started:.0f} စက္ကန့်")
                        st.success("Final MP4 ready. Final recap preview ကို ပြန်ဖွင့်နေပါတယ်…")
                        st.rerun()
                    except (ValueError, ImportError, OSError) as exc:
                        render_progress.empty()
                        render_timing.empty()
                        st.session_state.final_video = None
                        st.error(f"Render မပြီးသေးပါ: {exc}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="info" style="margin-top:.5rem;text-align:center">Use only media you own or have permission to process. Editing transformations do not remove copyright; provider access and download behavior depend on platform rules.</div>', unsafe_allow_html=True)
