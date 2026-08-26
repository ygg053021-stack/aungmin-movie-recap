from pathlib import Path

from .config import MAX_DURATION_SECONDS, MAX_UPLOAD_MB


def validate_media_file(path: str, duration_seconds: float) -> None:
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise ValueError("Video file is empty or could not be saved.")
    if file_path.stat().st_size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Video file must be {MAX_UPLOAD_MB} MB or smaller.")
    if duration_seconds <= 0:
        raise ValueError("The video duration could not be read. Try an MP4, MOV, WEBM, or MKV file.")
    if duration_seconds > MAX_DURATION_SECONDS:
        raise ValueError("This project accepts videos up to 5 minutes. Please choose a shorter video.")


def duration_notice(duration_seconds: float) -> str:
    if duration_seconds > 240:
        return "ဒီ video က ၅ မိနစ် limit နီးပါးဖြစ်သောကြောင့် processing အချိန်ပိုကြာနိုင်ပါတယ်။"
    return "Video ကြာချိန်သည် ၅ မိနစ်အောက်ဖြစ်ပါသည်။ Processing အချိန်သည် video resolution နှင့် server အခြေအနေပေါ်မူတည်ပါသည်။"
