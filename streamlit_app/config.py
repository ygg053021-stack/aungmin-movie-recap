from dataclasses import dataclass
from urllib.parse import urlparse

APP_NAME = "AungMin Movie Recap"
MODEL_NAME = "gemini-3.6-flash"
MAX_DURATION_SECONDS = 5 * 60
MAX_UPLOAD_MB = 200
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
    subtitle_mode: str = "Burmese only"
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
