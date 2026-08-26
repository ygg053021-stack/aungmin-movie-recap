import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .config import SourceInfo, SUPPORTED_DOMAINS

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


def prepare_quick_media(media_path: str) -> str:
    """Create a small analysis proxy so Quick Recap does not upload a huge original."""
    import imageio_ffmpeg
    source_duration = probe_duration(media_path)
    # Keep enough context for a short recap while preventing runaway uploads.
    max_seconds = min(max(source_duration, 1.0), 180.0) if source_duration else 180.0
    quick_path = str(Path(tempfile.gettempdir()) / f"aungmin-quick-{os.getpid()}.mp4")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-y", "-i", media_path, "-t", f"{max_seconds:.2f}",
        "-vf", "scale=-2:360,fps=2", "-c:v", "libx264", "-preset", "ultrafast",
        "-crf", "32", "-c:a", "aac", "-b:a", "48k", "-ac", "1", "-ar", "16000",
        "-movflags", "+faststart", quick_path,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Quick preview preparation timed out. Try a shorter video.") from exc
    if result.returncode != 0 or not Path(quick_path).exists():
        raise ValueError("Quick preview could not be prepared. Try an MP4 or a shorter video.")
    return quick_path


QUALITY_FORMATS = {
    "MP4 720p": "bv*[height<=720][ext=mp4]+ba/b[height<=720][ext=mp4]/best[height<=720]/best",
    "MP4 480p": "bv*[height<=480][ext=mp4]+ba/b[height<=480][ext=mp4]/best[height<=480]/best",
    "MP4 360p": "bv*[height<=360][ext=mp4]+ba/b[height<=360][ext=mp4]/best[height<=360]/best",
}


def download_authorized_source(url: str, quality: str = "MP4 720p") -> str:
    import yt_dlp
    workdir = tempfile.mkdtemp(prefix="aungmin-source-")
    output = str(Path(workdir) / "source.%(ext)s")
    ffmpeg_location = shutil.which("ffmpeg")
    if not ffmpeg_location:
        try:
            import imageio_ffmpeg
            ffmpeg_location = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_location = None
    options = {
        "outtmpl": output,
        "format": QUALITY_FORMATS.get(quality, QUALITY_FORMATS["MP4 720p"]) if ffmpeg_location else "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if ffmpeg_location:
        options["ffmpeg_location"] = ffmpeg_location
        options["merge_output_format"] = "mp4"
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([url])
    except Exception as exc:
        raise ValueError(f"Source could not be loaded. Use a public video you own or have permission to process. {exc}") from exc
    videos = [p for p in Path(workdir).glob("source.*") if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}]
    if not videos:
        raise ValueError("The provider did not return a playable video file.")
    # Preserve the provider's actual container so Gemini/FFmpeg receive the correct MIME type.
    target = Path(tempfile.gettempdir()) / f"aungmin-link-source{videos[0].suffix.lower()}"
    target.write_bytes(videos[0].read_bytes())
    return str(target)
