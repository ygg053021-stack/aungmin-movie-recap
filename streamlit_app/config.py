from dataclasses import dataclass
from urllib.parse import urlparse

APP_NAME = "AungMin Movie Recap"
MODEL_NAME = "gemini-3.7-flash"
MAX_DURATION_SECONDS = 5 * 60
MAX_UPLOAD_MB = 200
PLATFORMS = ("YouTube", "TikTok", "Bilibili", "RedNote", "Facebook", "Generic")
RATIOS = {"YouTube": "16:9", "TikTok": "9:16", "Bilibili": "16:9", "RedNote": "9:16", "Facebook": "1:1", "Generic": "16:9"}
VOICE_NAMES = ("my-MM-NilarNeural", "my-MM-ThihaNeural", "en-US-AriaNeural")
# These are real Unicode font families installed by packages.txt. Avoid Zawgyi,
# which produces rounded/missing glyphs when the text is Burmese Unicode.
FONT_FILES = {
    "OT43 YellYint Regular (1)": "OT43_YellYint-Regular.ttf",
    "OT43 YellYint Regular": "OT43_YellYint-Regular.ttf",
    "OT43 YellYint Thin": "OT43_YellYint-Thin.ttf",
    "Pyidaungsu Book Bold": "Pyidaungsu-Book-Bold.ttf",
    "Pyidaungsu Book Regular": "Pyidaungsu-Book-Regular.ttf",
    "SM01 WaTokeLay": "SM01_WaTokeLay-Regular.ttf",
    "SM02 KanBaung Regular (4)": "SM02_KanBaung-Regular.ttf",
    "SM02 KanBaung Regular": "SM02_KanBaung-Regular.ttf",
    "SM09 BeeZee": "SM09_BeeZee-Regular.ttf",
    "Thingaha 004": "Thingaha-004-Regular.ttf",
    "Z10 Cartoon": "Z10-Cartoon.ttf",
}
FONT_FAMILIES = {
    "OT43 YellYint Regular (1)": "OT43_YellYint",
    "OT43 YellYint Regular": "OT43_YellYint",
    "OT43 YellYint Thin": "OT43_YellYint",
    "Pyidaungsu Book Bold": "Pyidaungsu Book",
    "Pyidaungsu Book Regular": "Pyidaungsu Book",
    "SM01 WaTokeLay": "SM01_WaTokeLay",
    "SM02 KanBaung Regular (4)": "SM02_KanBaung",
    "SM02 KanBaung Regular": "SM02_KanBaung",
    "SM09 BeeZee": "SM09_BeeZee",
    "Thingaha 004": "Thingaha_004",
    "Z10 Cartoon": "Z10-Cartoon",
}
FONT_PRESETS = tuple(FONT_FILES)
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
    blur_enabled: bool = False
    subtitle_enabled: bool = True
    subtitle_auto_sync: bool = True
    subtitle_fill: str = "#FFF200"
    subtitle_outline: str = "#000000"
    subtitle_background: str = "#000000"
    subtitle_background_opacity: int = 0
    subtitle_design: str = "Yellow + black outline"
    blur_strength: int = 0
    blur_x: int = 5
    blur_y: int = 72
    blur_w: int = 90
    blur_h: int = 18
    subtitle_position: str = "Bottom"
    subtitle_mode: str = "Burmese only"
    subtitle_size: int = 52
    subtitle_font: str = "Pyidaungsu Book Regular"
    subtitle_offset: float = 0.0
    subtitle_x: int = 8
    subtitle_y: int = 78
    subtitle_w: int = 84
    subtitle_h: int = 16
    logo_position: str = "Top Right"
    logo_motion: str = "Slow drift"
    logo_x: int = 78
    logo_y: int = 5
    logo_w: int = 18
    watermark_text: str = ""
    watermark_x: int = 4
    watermark_y: int = 5
    watermark_size: int = 24
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
