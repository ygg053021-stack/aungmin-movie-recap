import re
from dataclasses import dataclass
from urllib.parse import urlparse

import streamlit as st

APP_NAME = "AungMin Movie Recap"
SUPPORTED = {
    "YouTube": ("youtube.com", "youtu.be"),
    "TikTok": ("tiktok.com",),
    "Bilibili": ("bilibili.com", "b23.tv"),
    "RedNote": ("xiaohongshu.com", "xhslink.com"),
}

@dataclass
class Source:
    url: str
    platform: str
    host: str


def platform_for(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    for name, domains in SUPPORTED.items():
        if host in domains or any(host.endswith("." + domain) for domain in domains):
            return name
    return "Other"


def inspect_url(url: str) -> Source:
    value = url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Link must start with https:// or http://")
    return Source(value, platform_for(value), parsed.netloc)


st.set_page_config(page_title=APP_NAME, page_icon="🎬", layout="wide")
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: radial-gradient(circle at 80% 0%, #123a43 0%, transparent 40%), linear-gradient(130deg, #080713, #170d2d 52%, #062f35); }
.block-container { max-width: 1400px; padding: 2rem 4rem 5rem; }
.brand { border-bottom: 1px solid #ffffff22; padding-bottom: 1rem; display:flex; justify-content:space-between; }
.brand b { letter-spacing:-.03em; } .meta { color:#82dfd1; font-size:.7rem; letter-spacing:.18em; text-transform:uppercase; }
.kicker { margin-top: 4rem; color:#73e3d3; letter-spacing:.28em; text-transform:uppercase; font-size:.68rem; }
.hero { font-size: clamp(3.4rem, 8vw, 8rem); line-height:.86; letter-spacing:-.09em; font-weight:800; margin:1.2rem 0; }
.hero span { background:linear-gradient(100deg,#fff,#c5a7ff,#5ce8d7); -webkit-background-clip:text; color:transparent; }
.copy { color:#aeb0c0; line-height:1.7; max-width:32rem; }
.card { border:1px solid #ffffff20; border-radius:22px; padding:1.4rem; background:#10162bd9; box-shadow:0 24px 70px #0005; }
.preview { min-height:260px; border:1px dashed #ffffff33; border-radius:18px; display:flex; align-items:center; justify-content:center; text-align:center; color:#9ba1b4; background:linear-gradient(145deg,#121a35,#071b25); }
</style>
""", unsafe_allow_html=True)

if "source" not in st.session_state:
    st.session_state.source = None
if "processed" not in st.session_state:
    st.session_state.processed = False

st.markdown(f'<div class="brand"><b>🎬 &nbsp;{APP_NAME}</b><span class="meta">Independent creator workspace</span></div>', unsafe_allow_html=True)
left, right = st.columns([1.05, 1], gap="large")
with left:
    st.markdown('<div class="kicker">Cinematic intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero">Turn stories<br>into <span>cinema.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="copy">Paste an authorized video link, shape the recap, review the final cut, and export only when you are ready.</div>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.caption("01  /  SOURCE")
    with st.form("source_form"):
        link = st.text_input("Video link", placeholder="YouTube · TikTok · Bilibili · RedNote")
        api_key = st.text_input("Google AI Studio API key", type="password", help="BYOK: keep your key private; this step does not save it to GitHub.")
        mode = st.radio("Workflow", ["AI Movie Recap", "Subtitle Only"], horizontal=True)
        fetch = st.form_submit_button("Get video source", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if fetch:
    if not api_key.strip():
        st.error("For the free BYOK plan, enter your Google AI Studio API key first.")
    else:
        try:
            st.session_state.source = inspect_url(link)
            st.session_state.processed = False
        except ValueError as exc:
            st.error(str(exc))

if st.session_state.source:
    st.divider()
    source = st.session_state.source
    st.subheader("Source preview")
    a, b = st.columns([1.08, .92], gap="large")
    with a:
        st.markdown(f'<div class="preview"><div><div style="font-size:2.4rem">▶</div><b>{source.platform} source accepted</b><br><small>{source.host}</small><br><small>Source adapter will fetch an authorized stream here.</small></div></div>', unsafe_allow_html=True)
    with b:
        st.caption("02  /  RECAP SETTINGS")
        language = st.selectbox("Language", ["Burmese", "English", "Thai", "Japanese", "Korean"])
        voice = st.selectbox("Voice", ["Cinematic narrator", "Conversational", "Dramatic", "Calm"])
        ratio = st.selectbox("Output ratio", ["YouTube · 16:9", "TikTok · 9:16", "Facebook · 1:1"])
        if st.button("Generate recap plan", type="primary", use_container_width=True):
            st.session_state.processed = True
            st.success(f"Recap plan ready · {language} · {voice} · {ratio}")

if st.session_state.processed:
    st.divider()
    st.subheader("Final preview gate")
    st.markdown('<div class="preview"><div><div style="font-size:2.4rem">▶</div><b>Preview ready before export</b><br><small>Connect the authorized fetch, AI, voice, and renderer adapters for real output.</small></div></div>', unsafe_allow_html=True)
    st.caption("Export remains behind the preview gate so you can review before downloading.")
    c1, c2, c3 = st.columns(3)
    c1.button("Export MP4", use_container_width=True)
    c2.button("Download WAV", use_container_width=True)
    c3.button("Download SRT", use_container_width=True)

st.caption("Use only video you own or are authorized to process. Provider access and download behavior depend on platform rules and configured adapters.")
