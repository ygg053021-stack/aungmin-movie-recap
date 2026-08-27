from pathlib import Path

from .config import MAX_DURATION_SECONDS, MAX_UPLOAD_MB


def validate_media_file(path: str, duration_seconds: float) -> None:
    """Validate media existence and readability without a product hard limit.

    Duration and size caps are intentionally optional deployment policy values.
    When the constants are None, the app accepts any readable media and lets the
    actual runtime/storage provider determine whether processing can complete.
    """
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise ValueError("Video file is empty or could not be saved.")
    if MAX_UPLOAD_MB is not None and file_path.stat().st_size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Video file exceeds the configured deployment limit of {MAX_UPLOAD_MB} MB.")
    if duration_seconds <= 0:
        raise ValueError("The video duration could not be read. Try an MP4, MOV, WEBM, or MKV file.")
    if MAX_DURATION_SECONDS is not None and duration_seconds > MAX_DURATION_SECONDS:
        raise ValueError("Video duration exceeds the configured deployment processing limit.")


def duration_notice(duration_seconds: float) -> str:
    minutes = max(0.1, float(duration_seconds or 0.0)) / 60
    return (
        f"Video ကြာချိန် {minutes:.1f} မိနစ် ဖြစ်ပါသည်။ Product-level မိနစ်အကန့်အသတ် မရှိပါ။ "
        "Processing ကြာချိန်သည် video အရွယ်အစား၊ resolution နဲ့ server/runtime အခြေအနေပေါ်မူတည်ပါသည်။"
    )
