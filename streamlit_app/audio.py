import asyncio
import os
import subprocess
import tempfile
from pathlib import Path


def wrap_caption(text: str, max_chars: int = 32) -> str:
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
    return "\n".join(lines)


def stamp(seconds: float) -> str:
    """Format a timestamp with millisecond precision for faithful subtitle timing."""
    total_ms = max(0, int(round(float(seconds or 0.0) * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def caption_units(bundle: dict, mode: str = "Burmese + English", max_chars: int = 32) -> list[str]:
    bn = [line.strip() for line in bundle.get("subtitle_bn", "").splitlines() if line.strip()]
    en = [line.strip() for line in bundle.get("subtitle_en", "").splitlines() if line.strip()]
    recap = [line.strip() for line in bundle.get("recap_bn", "").splitlines() if line.strip()]
    lines = bn or recap or ["AungMin Movie Recap"]
    units: list[str] = []
    for index, line in enumerate(lines):
        clean = " ".join(str(line).split())
        wrapped_lines = wrap_caption(clean, max_chars).splitlines() or [clean]
        english = en[index] if index < len(en) and mode == "Burmese + English" else ""
        if mode == "English only":
            wrapped_lines = wrap_caption(english or clean, max_chars).splitlines() or [english or clean]
        units.extend(line.strip() for line in wrapped_lines if line.strip())
        if english and mode == "Burmese + English":
            units.extend(line.strip() for line in wrap_caption(english, max_chars).splitlines() if line.strip())
    return units or ["AungMin Movie Recap"]


def caption_for_time(bundle: dict, timestamp: float, duration: float, mode: str = "Burmese + English", max_chars: int = 32) -> str:
    units = caption_units(bundle, mode, max_chars)
    position = max(0.0, min(0.999999, float(timestamp or 0.0) / max(1.0, float(duration or 1.0))))
    return units[min(len(units) - 1, int(position * len(units)))]


def _timed_caption_chunks(burmese: str, english: str, mode: str, max_chars: int) -> list[str]:
    """Keep each bilingual caption event compact without dropping text."""
    bn_lines = wrap_caption(burmese, max_chars).splitlines() if burmese else []
    en_lines = wrap_caption(english, max_chars).splitlines() if english else []
    if mode == "English only":
        return ["\n".join(en_lines[i:i + 3]) for i in range(0, len(en_lines), 3)] or ["\n".join(bn_lines[:3])]
    if mode == "Burmese only":
        return ["\n".join(bn_lines[i:i + 3]) for i in range(0, len(bn_lines), 3)] or ["AungMin Movie Recap"]
    count = max((len(bn_lines) + 2) // 3, (len(en_lines) + 2) // 3, 1)
    chunks: list[str] = []
    for index in range(count):
        bn_chunk = "\n".join(bn_lines[index * 3:(index + 1) * 3])
        en_chunk = "\n".join(en_lines[index * 3:(index + 1) * 3])
        if bn_chunk and en_chunk:
            chunks.append(f"{{\\1c&H0000F2FF&}}{bn_chunk}\n{{\\1c&H00FFFFFF&}}{en_chunk}")
        elif bn_chunk:
            chunks.append(f"{{\\1c&H0000F2FF&}}{bn_chunk}")
        elif en_chunk:
            chunks.append(f"{{\\1c&H00FFFFFF&}}{en_chunk}")
    return chunks or ["AungMin Movie Recap"]


def make_srt(
    bundle: dict,
    duration: float,
    path: str,
    offset: float = 0.0,
    mode: str = "Burmese + English",
    max_chars: int = 32,
    subtitle_box: tuple[float, float, float, float] | None = None,
    output_size: tuple[int, int] | None = None,
) -> None:
    lines = caption_units(bundle, mode, max_chars)
    duration = max(1.0, float(duration or len(lines) * 4))
    en = [line.strip() for line in bundle.get("subtitle_en", "").splitlines() if line.strip()]
    raw_segments = bundle.get("segments")
    timed_segments = []
    if isinstance(raw_segments, list):
        for segment_index, item in enumerate(raw_segments):
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                continue
            try:
                start_value = max(0.0, float(item.get("start", 0.0)))
                end_value = min(duration, float(item.get("end", duration)))
            except (TypeError, ValueError):
                continue
            if end_value > start_value:
                burmese = str(item.get("text", "")).strip()
                english = ""
                if mode == "Burmese + English":
                    english = str(item.get("text_en", "")).strip()
                    if not english and segment_index < len(en):
                        english = en[segment_index]
                elif mode == "English only":
                    english = str(item.get("text_en", "")).strip() or (en[segment_index] if segment_index < len(en) else "")
                    burmese = english or burmese
                chunks = _timed_caption_chunks(burmese, english, mode, max_chars)
                chunk_duration = max(0.1, (end_value - start_value) / len(chunks))
                for chunk_index, caption in enumerate(chunks):
                    chunk_start = start_value + chunk_index * chunk_duration + offset
                    chunk_end = min(end_value + offset, start_value + (chunk_index + 1) * chunk_duration + offset)
                    timed_segments.append((max(0.0, chunk_start), max(chunk_start + 0.05, chunk_end), caption))
    with open(path, "w", encoding="utf-8") as handle:
        entries = timed_segments or [
            (max(0.0, (index - 1) * duration / len(lines) + offset),
             min(duration, max((index - 1) * duration / len(lines) + offset + 0.5, index * duration / len(lines) + offset)),
             line)
            for index, line in enumerate(lines, 1)
        ]
        for index, (start, end, line) in enumerate(entries, 1):
            # Never truncate approved subtitle text; timing and line wrapping are
            # handled before this point so the SRT retains the complete content.
            caption = wrap_caption(line, max_chars)
            if subtitle_box and output_size:
                box_x, box_y, _box_w, _box_h = subtitle_box
                output_width, output_height = output_size
                x = max(0, min(output_width - 1, int(round(float(box_x) / 100 * output_width))))
                y = max(0, min(output_height - 1, int(round(float(box_y) / 100 * output_height))))
                box_width = max(1, int(round(float(_box_w) / 100 * output_width)))
                box_height = max(1, int(round(float(_box_h) / 100 * output_height)))
                caption = f"{{\\an5\\pos({x + box_width // 2},{y + box_height // 2})}}{caption}"
            handle.write(f"{index}\n{stamp(start)} --> {stamp(end)}\n{caption}\n\n")


def make_ass(
    bundle: dict,
    duration: float,
    path: str,
    offset: float = 0.0,
    mode: str = "Burmese + English",
    max_chars: int = 32,
    subtitle_box: tuple[float, float, float, float] | None = None,
    output_size: tuple[int, int] | None = None,
    font_name: str = "Noto Sans Myanmar",
    font_size: int = 52,
    fill: str = "&H0000F2FF",
    outline: str = "&H00000000",
    outline_width: int = 3,
) -> None:
    """Write an ASS subtitle file whose PlayRes is exactly the output canvas."""
    from tempfile import TemporaryDirectory

    output_width, output_height = output_size or (1920, 1080)
    with TemporaryDirectory(prefix="aungmin-ass-") as temp_dir:
        srt_path = Path(temp_dir) / "captions.srt"
        make_srt(bundle, duration, str(srt_path), offset, mode, max_chars, subtitle_box, output_size)
        blocks = [block.strip() for block in srt_path.read_text(encoding="utf-8").split("\n\n") if block.strip()]
        events: list[str] = []
        for block in blocks:
            rows = block.splitlines()
            if len(rows) < 3 or "-->" not in rows[1]:
                continue
            start_raw, end_raw = [value.strip() for value in rows[1].split("-->", 1)]
            def ass_time(raw: str) -> str:
                hours, minutes, seconds = raw.replace(",", ".").split(":")
                return f"{int(hours)}:{int(minutes):02d}:{float(seconds):05.2f}"
            text = r"\N".join(rows[2:])
            events.append(f"Dialogue: 0,{ass_time(start_raw)},{ass_time(end_raw)},Default,,0,0,0,,{text}")

    ass = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {output_width}",
            f"PlayResY: {output_height}",
            "ScaledBorderAndShadow: yes",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,{font_name},{max(8, min(140, int(font_size)))},{fill},&H000000FF,{outline},&HFF000000,0,0,0,0,100,100,0,0,1,{max(0, min(12, int(outline_width)))},1,7,0,0,0,1",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
            *events,
            "",
        ]
    )
    Path(path).write_text(ass, encoding="utf-8")


def create_voiceover(script: str, path: str, voice_name: str) -> None:
    try:
        import edge_tts

        async def save_audio() -> None:
            # Do not slice approved text: silent truncation makes the narration
            # disagree with the script and leaves the final story incomplete.
            await asyncio.wait_for(edge_tts.Communicate(script, voice_name).save(path), timeout=120)

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


def pad_or_trim_audio_to_duration(input_path: str, output_path: str, target_seconds: float) -> float:
    """Match track length without changing speaking tempo or pitch."""
    from .media import probe_duration
    import imageio_ffmpeg

    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise ValueError("Voiceover input file မတွေ့ပါ။")
    target = max(0.5, float(target_seconds or 0.0))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-y", "-i", str(source),
        "-filter:a", f"apad,atrim=duration={target:.3f}",
        "-t", f"{target:.3f}", "-vn", "-c:a", "libmp3lame", "-b:a", "128k", str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size < 128:
        raise ValueError(f"Voice duration padding failed: {result.stderr[-500:]}")
    measured = probe_duration(str(destination))
    if measured <= 0:
        raise ValueError("ချိန်ညှိပြီး voice duration ကို မဖတ်နိုင်ပါ။")
    return measured


def fit_audio_preserving_script(input_path: str, output_path: str, target_seconds: float, max_speed_delta: float = 0.18) -> float:
    """Fit narration without dropping words.

    Short narration is padded with silence. Slightly long narration is sped up by
    one bounded, uniform factor. If it would require a larger change, fail clearly
    instead of silently trimming the approved script.
    """
    from .media import probe_duration

    actual = probe_duration(input_path)
    target = max(0.5, float(target_seconds or 0.0))
    if actual <= 0:
        raise ValueError("Voiceover ကြာချိန်ကို မဖတ်နိုင်ပါ။")
    if actual <= target:
        return pad_or_trim_audio_to_duration(input_path, output_path, target)
    required_speed = actual / target
    if required_speed > 1.0 + max(0.01, float(max_speed_delta)):
        raise ValueError(
            f"Approved narration သည် video ထက် {actual - target:.1f} စက္ကန့်ရှည်နေပါသည်။ "
            "စာသားမဖြတ်ဘဲ အသံကို အလွန်မြန်အောင်မလုပ်နိုင်သောကြောင့် script ကို အနည်းငယ်တိုအောင် ပြင်ပြီး Voice ကို ပြန် approve လုပ်ပါ။"
        )
    return fit_audio_to_duration(input_path, output_path, target)


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
