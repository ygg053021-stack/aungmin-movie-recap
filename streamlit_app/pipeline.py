from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Callable

from .audio import create_voiceover, fit_audio_preserving_script, make_srt, pad_or_trim_audio_to_duration
from .config import EditorState
from .render import render_mp4
from .media import probe_duration


ProgressCallback = Callable[[int, str, float], None]


def render_voice_preview(
    media_path: str,
    bundle: dict,
    voice_name: str,
    editor: EditorState,
    output_platform: str,
    progress: ProgressCallback | None = None,
) -> dict:
    """Create a reviewable voice-only recap preview using approved script text.

    The original audio is replaced by the generated Burmese narration. Finish-stage
    subtitles and blur are intentionally deferred until the user approves the voice.
    """
    recap = str(bundle.get("recap_bn", "")).strip()
    if not recap:
        raise ValueError("အတည်ပြုထားသော Burmese recap script မရှိသေးပါ။")
    if not media_path or not Path(media_path).is_file():
        raise ValueError("Voice preview အတွက် original video file မတွေ့ပါ။")
    root = Path(tempfile.gettempdir()) / "aungmin-approved-voice"
    root.mkdir(parents=True, exist_ok=True)
    voice_path = root / "approved-voice-raw.mp3"
    fitted_voice_path = root / "approved-voice.mp3"
    output_path = root / "approved-voice-preview.mp4"
    started = time.monotonic()
    if progress:
        progress(12, "အတည်ပြုထားသော script မှ မြန်မာအသံ ဖန်တီးနေသည်", started)
    # Generate one continuous narration. Per-scene atempo fitting made late
    # segments sound rushed and caused the speaking pace to jump.
    source_duration = probe_duration(media_path)
    if source_duration <= 0:
        raise ValueError("Original video duration ကို မဖတ်နိုင်ပါ။")
    create_voiceover(recap, str(voice_path), voice_name)
    if progress:
        progress(42, f"Narration ကို မူရင်း {source_duration:.1f} စက္ကန့်နဲ့ pace မပြောင်းဘဲ ချိန်နေသည်", started)
    fit_audio_preserving_script(str(voice_path), str(fitted_voice_path), source_duration)
    if progress:
        progress(55, "မူရင်းအသံကို ဖယ်ပြီး duration တူ recap voice preview ပေါင်းနေသည်", started)
    ratio = {"YouTube": "16:9", "TikTok": "9:16", "Facebook": "1:1"}.get(output_platform, "16:9")
    preview_editor = EditorState(speed=1.0, flip=False, blur_strength=0)
    # No.3 is voice-only: omit subtitles entirely. Finish creates the valid SRT.
    render_mp4(media_path, None, str(fitted_voice_path), str(output_path), preview_editor, ratio)
    if not output_path.is_file() or output_path.stat().st_size < 1024:
        raise ValueError("Voice preview MP4 မဖန်တီးနိုင်ပါ။")
    if progress:
        progress(100, "Voice preview အဆင်သင့်ဖြစ်ပါပြီ", started)
    return {
        "voice_path": str(fitted_voice_path),
        "voice_bytes": fitted_voice_path.read_bytes(),
        "video_bytes": output_path.read_bytes(),
        "source_duration": source_duration,
        "voice_duration": probe_duration(str(fitted_voice_path)),
    }


def render_bundle_to_mp4(
    media_path: str,
    bundle: dict,
    voice_name: str,
    editor: EditorState,
    output_platform: str,
    progress: ProgressCallback | None = None,
    logo_path: str | None = None,
    approved_voice_path: str | None = None,
) -> bytes:
    """Create and verify the final MP4 from one completed recap bundle.

    This function deliberately keeps every intermediate artifact in one temporary
    directory and only returns bytes after FFmpeg has created a non-empty file.
    """
    if not media_path or not Path(media_path).is_file():
        raise ValueError("Original video file မတွေ့ပါ။ Final MP4 ထုတ်ရန် video upload လိုပါမယ်။")
    recap = str(bundle.get("recap_bn", "")).strip()
    if not recap:
        raise ValueError("Burmese recap script မရှိသေးပါ။ Quick Recap ကို အရင်လုပ်ပါ။")

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="aungmin-one-click-") as workdir:
        root = Path(workdir)
        srt_path = root / "captions.srt"
        raw_voice_path = root / "voice-raw.mp3"
        voice_path = root / "voice.mp3"
        output_path = root / "aungmin-recap.mp4"
        duration = probe_duration(media_path)
        if not duration or duration <= 0:
            raise ValueError("Video ကြာချိန်ကို မဖတ်နိုင်ပါ။ MP4 ဖိုင်ကို ပြန်တင်ပါ။")

        if progress:
            progress(10, "Video ကို စစ်နေသည်", started)
        if progress:
            progress(25, "မြန်မာအသံ ဖန်တီးနေသည်", started)
        if approved_voice_path and Path(approved_voice_path).is_file():
            raw_voice_path.write_bytes(Path(approved_voice_path).read_bytes())
        else:
            create_voiceover(recap, str(raw_voice_path), voice_name)
        if not raw_voice_path.is_file() or raw_voice_path.stat().st_size < 1024:
            raise ValueError("မြန်မာအသံဖိုင် မဖန်တီးနိုင်ပါ။")
        if progress:
            progress(40, f"Narration ကို မူရင်း {duration:.1f} စက္ကန့်နဲ့ ချိန်နေသည်", started)
        fit_audio_preserving_script(str(raw_voice_path), str(voice_path), duration)

        # The approved voice is fitted to source duration, so captions use the
        # source timeline exactly instead of drifting with raw TTS length.
        voice_duration = probe_duration(str(voice_path))
        make_srt(bundle, duration, str(srt_path), editor.subtitle_offset, editor.subtitle_mode)
        if not srt_path.is_file() or srt_path.stat().st_size == 0:
            raise ValueError("မြန်မာစာတန်းထိုး SRT ဖိုင် မဖန်တီးနိုင်ပါ။")

        if progress:
            progress(55, "1080p / 30 FPS MP4 ပေါင်းနေသည်", started)
        ratio = {"YouTube": "16:9", "TikTok": "9:16", "Facebook": "1:1"}.get(output_platform, "16:9")
        render_mp4(media_path, str(srt_path), str(voice_path), str(output_path), editor, ratio, logo_path=logo_path)
        if not output_path.is_file() or output_path.stat().st_size < 1024:
            raise ValueError("FFmpeg ပြီးသွားသော်လည်း အမှန်တကယ် MP4 output မရပါ။")
        data = output_path.read_bytes()
        if not data.startswith(b"\x00\x00\x00"):
            raise ValueError("ထုတ်ထားသောဖိုင်သည် valid MP4 မဟုတ်ပါ။")
        if progress:
            progress(100, "Final MP4 အဆင်သင့်ဖြစ်ပါပြီ", started)
        return data
