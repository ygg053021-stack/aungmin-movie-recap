import asyncio
import os
import subprocess
import tempfile
from pathlib import Path


def _wrap_caption(text: str, max_chars: int = 22) -> str:
    """Keep Burmese captions compact enough for portrait and landscape output."""
    compact = " ".join(str(text or "").replace("\n", " ").split())
    if len(compact) <= max_chars:
        return compact
    # Burmese often has no spaces, so wrap by Unicode characters when a space
    # based split cannot produce short lines.
    words = compact.split(" ") if " " in compact else list(compact)
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if " " in compact else current + word
        if current and len(candidate) > max_chars:
            lines.append(current.strip())
            current = word
        else:
            current = candidate
    if current:
        lines.append(current.strip())
    return "\n".join(lines[:3])


def stamp(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"00:{total // 60:02d}:{total % 60:02d},000"


def make_srt(bundle: dict, duration: float, path: str, offset: float = 0.0, mode: str = "Burmese + English") -> None:
    bn = [line.strip() for line in bundle.get("subtitle_bn", "").splitlines() if line.strip()]
    en = [line.strip() for line in bundle.get("subtitle_en", "").splitlines() if line.strip()]
    recap = [line.strip() for line in bundle.get("recap_bn", "").splitlines() if line.strip()]
    # Auto mode consumes the approved narration timeline. If the model returned
    # one long paragraph, split it into compact caption units before distributing
    # them over the exact fitted voice duration.
    lines = bn or recap or ["AungMin Movie Recap"]
    normalized: list[str] = []
    for line in lines:
        clean = " ".join(str(line).split())
        if len(clean) <= 42:
            normalized.append(clean)
        else:
            normalized.extend([part.replace("\n", " ").strip() for part in _wrap_caption(clean, 22).splitlines() if part.strip()])
    lines = normalized or ["AungMin Movie Recap"]
    duration = max(1.0, float(duration or len(lines) * 4))
    raw_segments = bundle.get("segments")
    timed_segments = []
    if isinstance(raw_segments, list):
        for item in raw_segments:
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                continue
            try:
                start_value = max(0.0, float(item.get("start", 0.0)))
                end_value = min(duration, float(item.get("end", duration)))
            except (TypeError, ValueError):
                continue
            if end_value > start_value:
                timed_segments.append((max(0.0, start_value + offset), min(duration, end_value + offset), str(item["text"]).strip()))
    with open(path, "w", encoding="utf-8") as handle:
        entries = timed_segments or [
            (max(0.0, (index - 1) * duration / len(lines) + offset),
             min(duration, max((index - 1) * duration / len(lines) + offset + 0.5, index * duration / len(lines) + offset)),
             line)
            for index, line in enumerate(lines, 1)
        ]
        for index, (start, end, line) in enumerate(entries, 1):
            english = en[index - 1] if index - 1 < len(en) else ""
            if mode == "Burmese only":
                english = ""
            if mode == "English only":
                line = english or line
            caption = _wrap_caption(line[:220]) + (f"\n{_wrap_caption(english[:220])}" if english and mode == "Burmese + English" else "")
            handle.write(f"{index}\n{stamp(start)} --> {stamp(end)}\n{caption}\n\n")


def create_voiceover(script: str, path: str, voice_name: str) -> None:
    try:
        import edge_tts

        async def save_audio() -> None:
            await asyncio.wait_for(edge_tts.Communicate(script[:8000], voice_name).save(path), timeout=120)

        asyncio.run(save_audio())
        if not os.path.isfile(path) or os.path.getsize(path) < 128:
            raise ValueError("Voiceover finished without creating an audio file.")
    except asyncio.TimeoutError as exc:
        raise ValueError("မြန်မာ voiceover ထုတ်ချိန် timeout ဖြစ်သွားပါတယ်။ Script ကိုတိုအောင်လုပ်ပြီး ပြန်စမ်းပါ။") from exc
    except Exception as exc:
        raise ValueError(f"Voiceover generation failed. Check the selected voice or server connection. {exc}") from exc


def _atempo_chain(factor: float) -> str:
    """Return an FFmpeg atempo chain that supports rates outside 0.5–2.0."""
    remaining = max(0.05, float(factor))
    filters: list[str] = []
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    if abs(remaining - 1.0) > 0.005:
        filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters) or "anull"


def fit_audio_to_duration(input_path: str, output_path: str, target_seconds: float) -> float:
    """Time-stretch narration to target duration and return the measured result.

    The source video remains unchanged; only the generated narration is stretched
    with an FFmpeg atempo chain and trimmed to the exact source duration.
    """
    from .media import probe_duration
    import imageio_ffmpeg

    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise ValueError("Voiceover input file မတွေ့ပါ။")
    target = max(0.5, float(target_seconds or 0.0))
    actual = probe_duration(str(source))
    if actual <= 0 or target <= 0:
        raise ValueError("Voiceover ကြာချိန်ကို မဖတ်နိုင်ပါ။")
    factor = actual / target
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    temp_path = Path(tempfile.mkstemp(prefix="aungmin-fit-", suffix=".mp3")[1])
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-filter:a",
        f"{_atempo_chain(factor)},apad,atrim=duration={target:.3f}",
        "-t",
        f"{target:.3f}",
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(temp_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if result.returncode != 0 or not temp_path.is_file() or temp_path.stat().st_size < 128:
            raise ValueError(f"Voice duration fit failed: {result.stderr[-500:]}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(temp_path.read_bytes())
    finally:
        temp_path.unlink(missing_ok=True)
    measured = probe_duration(str(destination))
    if measured <= 0:
        raise ValueError("ချိန်ညှိပြီး voice duration ကို မဖတ်နိုင်ပါ။")
    return measured


def create_segmented_voiceover(segments: list[dict], path: str, voice_name: str, duration: float) -> None:
    """Render timestamped narration segments into one source-duration audio track."""
    if not segments:
        raise ValueError("Scene narration segments မရှိသေးပါ။")
    from .media import probe_duration
    import imageio_ffmpeg

    root = Path(tempfile.mkdtemp(prefix="aungmin-segments-"))
    clip_paths: list[tuple[float, Path]] = []
    try:
        for index, segment in enumerate(segments):
            text = str(segment.get("text", "")).strip()
            start = max(0.0, float(segment.get("start", 0.0)))
            end = min(float(duration), float(segment.get("end", duration)))
            if not text or end <= start:
                continue
            raw = root / f"segment-{index:03d}-raw.mp3"
            fit = root / f"segment-{index:03d}.mp3"
            create_voiceover(text, str(raw), voice_name)
            fit_audio_to_duration(str(raw), str(fit), end - start)
            clip_paths.append((start, fit))

        if not clip_paths:
            raise ValueError("Valid scene narration segments မရှိသေးပါ။")
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        inputs: list[str] = []
        filters: list[str] = []
        for index, (start, clip) in enumerate(clip_paths):
            inputs.extend(["-i", str(clip)])
            delay_ms = max(0, int(round(start * 1000)))
            filters.append(f"[{index}:a]adelay={delay_ms}:all=1[a{index}]")
        labels = "".join(f"[a{index}]" for index in range(len(clip_paths)))
        filters.append(f"{labels}amix=inputs={len(clip_paths)}:duration=longest:dropout_transition=0,apad,atrim=duration={float(duration):.3f}[aout]")
        command = [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[aout]", "-t", f"{float(duration):.3f}", "-c:a", "libmp3lame", "-b:a", "128k", path]
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 or not Path(path).is_file() or Path(path).stat().st_size < 128:
            raise ValueError(f"Scene narration render failed: {result.stderr[-500:]}")
        if probe_duration(path) <= 0:
            raise ValueError("Scene narration output duration ကို မဖတ်နိုင်ပါ။")
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)
