from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Callable

from .audio import create_voiceover, make_srt
from .config import EditorState
from .render import render_mp4
from .media import probe_duration


ProgressCallback = Callable[[int, str, float], None]


def render_bundle_to_mp4(
    media_path: str,
    bundle: dict,
    voice_name: str,
    editor: EditorState,
    output_platform: str,
    progress: ProgressCallback | None = None,
    logo_path: str | None = None,
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
        voice_path = root / "voice.mp3"
        output_path = root / "aungmin-recap.mp4"
        duration = probe_duration(media_path)
        if not duration or duration <= 0:
            raise ValueError("Video ကြာချိန်ကို မဖတ်နိုင်ပါ။ MP4 ဖိုင်ကို ပြန်တင်ပါ။")

        if progress:
            progress(10, "Video ကို စစ်နေသည်", started)
        if progress:
            progress(25, "မြန်မာအသံ ဖန်တီးနေသည်", started)
        create_voiceover(recap, str(voice_path), voice_name)
        if not voice_path.is_file() or voice_path.stat().st_size < 1024:
            raise ValueError("မြန်မာအသံဖိုင် မဖန်တီးနိုင်ပါ။")

        # Generate captions against the actual TTS duration. Equal chunks over
        # source duration made subtitles drift when TTS finished early/late.
        voice_duration = probe_duration(str(voice_path))
        subtitle_duration = min(duration, voice_duration) if voice_duration > 0 else duration
        make_srt(bundle, subtitle_duration, str(srt_path), editor.subtitle_offset, editor.subtitle_mode)
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
