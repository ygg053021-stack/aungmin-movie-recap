import base64
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageFont

from .config import EditorState, FONT_FAMILIES, SourceInfo


def _output_size(ratio: str) -> tuple[int, int]:
    if ratio == "9:16":
        return 1080, 1920
    if ratio == "1:1":
        return 1080, 1080
    if ratio == "3:4":
        return 1080, 1440
    return 1920, 1080


def _ass_color(value: str, alpha: int = 0) -> str:
    raw = str(value or "#FFFFFF").lstrip("#")
    if len(raw) != 6:
        raw = "FFFFFF"
    rr, gg, bb = raw[0:2], raw[2:4], raw[4:6]
    return f"&H{max(0, min(255, int(alpha))):02X}{bb}{gg}{rr}"


def _subtitle_filter(srt_path: str, effects: EditorState, output_width: int = 1920, output_height: int = 1080) -> str:
    safe_path = srt_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    selected = getattr(effects, "subtitle_font", "Pyidaungsu Book Regular") or "Pyidaungsu Book Regular"
    font = FONT_FAMILIES.get(selected, "Pyidaungsu Book").replace("'", "")
    fonts_dir = (Path(__file__).resolve().parent.parent / "fonts").as_posix().replace("'", "\\'")
    # Fabric preview scales from the selected output canvas. Use the same
    # output-relative font size and top-left anchor in FFmpeg/ASS so a drag in
    # preview lands at the same place in the final MP4.
    # Keep the same output-relative size formula as the Fabric preview.
    # A 16px floor made 9:16 sizes collapse to one visible size.
    size = max(8, min(140, int(round(getattr(effects, "subtitle_size", 52) * output_width / 1920 * 1.35))))
    custom_x = max(0, min(99, int(getattr(effects, "subtitle_x", 8))))
    custom_y = max(0, min(99, int(getattr(effects, "subtitle_y", 78))))
    margin_l = int(round(custom_x * output_width / 100))
    margin_v = int(round(custom_y * output_height / 100))
    custom_w = max(5, min(100 - custom_x, int(getattr(effects, "subtitle_w", 84))))
    margin_r = max(0, output_width - margin_l - int(round(custom_w * output_width / 100)))
    fill = _ass_color(getattr(effects, "subtitle_fill", "#FFF200"), 0)
    outline = _ass_color(getattr(effects, "subtitle_outline", "#000000"), 0)
    background_alpha = 255 - max(0, min(255, int(getattr(effects, "subtitle_background_opacity", 0) * 2.55)))
    background = _ass_color(getattr(effects, "subtitle_background", "#000000"), background_alpha)
    if Path(srt_path).suffix.lower() == ".ass":
        return f"ass='{safe_path}':fontsdir='{fonts_dir}'"
    # The subtitle panel is drawn as a separate video layer. ASS BorderStyle=3
    # creates a black rectangle per wrapped line, which is not the reference look
    # and can cover the source frame. Keep ASS text transparent and let the panel
    # use the full normalized subtitle box.
    style = f"FontName={font},FontSize={size},PrimaryColour={fill},OutlineColour={outline},BackColour=&HFF000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=7,MarginL=0,MarginV=0,MarginR=0"
    return f"subtitles='{safe_path}':fontsdir='{fonts_dir}':original_size={output_width}x{output_height}:force_style='{style}'"


def _prepare_watermark_png(text: str, font_path: str, font_size: int, output_path: str) -> str:
    """Render Burmese watermark text to a transparent PNG so drawtext is not required."""
    size = max(12, min(96, int(font_size)))
    try:
        font = ImageFont.truetype(font_path, size=size)
    except Exception:
        font = ImageFont.load_default()
    probe = Image.new("RGBA", (2400, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text[:80], font=font, stroke_width=2)
    width = max(80, bbox[2] - bbox[0] + 24)
    height = max(48, bbox[3] - bbox[1] + 24)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((12 - bbox[0], 12 - bbox[1]), text[:80], font=font, fill=(255, 255, 255, 184), stroke_width=2, stroke_fill=(0, 0, 0, 140))
    canvas.save(output_path, format="PNG", optimize=True)
    return output_path


def _video_graph(source_path: str, srt_path: str | None, effects: EditorState, ratio: str, target_fps: int) -> str:
    width, height = _output_size(ratio)
    if ratio in {"9:16", "3:4"}:
        # Fill portrait canvas like the reference edit, then crop the sides;
        # do not letterbox a landscape source into a narrow portrait frame.
        pre = [f"scale={width}:{height}:force_original_aspect_ratio=increase", f"crop={width}:{height}", f"fps={target_fps}"]
    else:
        pre = [f"scale={width}:{height}:force_original_aspect_ratio=decrease", f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black", f"fps={target_fps}"]
    if effects.flip:
        pre.append("hflip")
    # Aspect-ratio crop is already included above for portrait outputs.
    if effects.speed != 1.0:
        pre.append(f"setpts=PTS/{max(0.25, min(4.0, effects.speed))}")
    subtitle_enabled = getattr(effects, "subtitle_enabled", True) and srt_path and Path(srt_path).is_file() and Path(srt_path).stat().st_size > 0
    subtitle = _subtitle_filter(srt_path, effects, width, height) if subtitle_enabled else ""
    subtitle_panel = ""
    if subtitle_enabled and getattr(effects, "subtitle_background_opacity", 0) > 0:
        panel_x = max(0.0, min(0.95, effects.subtitle_x / 100))
        panel_y = max(0.0, min(0.95, effects.subtitle_y / 100))
        panel_w = max(0.03, min(1.0 - panel_x, effects.subtitle_w / 100))
        panel_h = max(0.03, min(1.0 - panel_y, effects.subtitle_h / 100))
        panel_alpha = max(0.0, min(1.0, effects.subtitle_background_opacity / 100))
        subtitle_panel = f"drawbox=x=iw*{panel_x:.4f}:y=ih*{panel_y:.4f}:w=iw*{panel_w:.4f}:h=ih*{panel_h:.4f}:color=black@{panel_alpha:.3f}:t=fill"
    subtitle_chain = ",".join(filter(None, (subtitle_panel, subtitle)))
    if (getattr(effects, "blur_enabled", False) or effects.blur_strength > 0) and effects.blur_strength > 0:
        x = max(0.0, min(0.95, effects.blur_x / 100))
        y = max(0.0, min(0.95, effects.blur_y / 100))
        w = max(0.03, min(1.0 - x, effects.blur_w / 100))
        h = max(0.03, min(1.0 - y, effects.blur_h / 100))
        # Use a strong blur regardless of a small slider value; the region must
        # hide the original subtitle completely before Burmese text is added.
        radius = max(12, min(30, int(effects.blur_strength)))
        graph = (
            f"[0:v]{','.join(pre)}[base];"
            f"[base]split=2[clean][blur];"
            f"[blur]crop=w=iw*{w:.4f}:h=ih*{h:.4f}:x=iw*{x:.4f}:y=ih*{y:.4f},boxblur={radius}:2,drawbox=x=0:y=0:w=iw:h=ih:color=black@0.16:t=fill[blurred];"
            f"[clean][blurred]overlay=x=main_w*{x:.4f}:y=main_h*{y:.4f}:shortest=1[blurred_base];"
        )
        return graph + (f"[blurred_base]{subtitle_chain}[vbase]" if subtitle_chain else "[blurred_base]null[vbase]")
    return f"[0:v]{','.join(pre + ([subtitle_chain] if subtitle_chain else []))}[vbase]"


def render_mp4(source_path: str, srt_path: str | None, voice_path: str | None, output_path: str, effects: EditorState, ratio: str, music_path: str | None = None, target_width: int = 1920, target_height: int = 1080, target_fps: int = 30, logo_path: str | None = None) -> None:
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    source_duration = 0.0
    try:
        from .media import probe_duration
        source_duration = probe_duration(source_path)
    except Exception:
        pass

    graph_parts = [_video_graph(source_path, srt_path, effects, ratio, target_fps)]
    command = [ffmpeg, "-y", "-i", source_path]
    if voice_path:
        command += ["-i", voice_path]
    if music_path:
        command += ["-i", music_path]
    watermark = str(getattr(effects, "watermark_text", "") or "").strip()
    watermark_index = None
    if watermark:
        watermark_font = Path(__file__).resolve().parent.parent / "fonts" / "Pyidaungsu-Book-Regular.ttf"
        watermark_file = Path(output_path).with_suffix(".watermark.png")
        _prepare_watermark_png(watermark, str(watermark_font), int(getattr(effects, "watermark_size", 24)), str(watermark_file))
        watermark_index = 1 + int(bool(voice_path)) + int(bool(music_path))
        command += ["-loop", "1", "-i", str(watermark_file)]
    logo_index = None
    if logo_path:
        logo_index = 1 + int(bool(voice_path)) + int(bool(music_path)) + int(watermark_index is not None)
        command += ["-loop", "1", "-i", logo_path]
    current_video = "[vbase]"
    if watermark_index is not None:
        wx = max(0, min(100, int(getattr(effects, "watermark_x", 4))))
        wy = max(0, min(100, int(getattr(effects, "watermark_y", 5))))
        graph_parts.append(f"[{watermark_index}:v]format=rgba,colorchannelmixer=aa=0.82[watermark];[vbase][watermark]overlay=x=main_w*{wx/100:.4f}:y=main_h*{wy/100:.4f}:shortest=1[vwatermarked]")
        current_video = "[vwatermarked]"
    if logo_path:
        position = getattr(effects, "logo_position", "Top Right")
        motion = getattr(effects, "logo_motion", "Slow drift")
        logo_x = max(0, min(95, int(getattr(effects, "logo_x", 78))))
        logo_y = max(0, min(95, int(getattr(effects, "logo_y", 5))))
        logo_w = max(5, min(60, int(getattr(effects, "logo_w", 18))))
        x, y = f"main_w*{logo_x/100:.4f}", f"main_h*{logo_y/100:.4f}"
        if motion == "Slow drift":
            x = f"{x}+12*sin(t/5)" if x != "28" else "28+12*sin(t/5)"
            y = f"{y}+8*sin(t/6)" if y != "28" else "28+8*sin(t/6)"
        logo_index = logo_index if logo_index is not None else 1 + int(bool(voice_path)) + int(bool(music_path))
        graph_parts.append(f"[{logo_index}:v]format=rgba,scale=iw*{logo_w/100:.4f}:-1,colorchannelmixer=aa=0.82[logo];{current_video}[logo]overlay=x='{x}':y='{y}':shortest=1[vout]")
    elif current_video == "[vbase]":
        graph_parts[0] = graph_parts[0].replace("[vbase]", "[vout]")
    else:
        graph_parts.append(f"{current_video}null[vout]")
    if voice_path and music_path:
        graph_parts.append("[1:a]volume=1.0[voice];[2:a]volume=0.18[music];[voice][music]amix=inputs=2:duration=longest[aout]")
    command += ["-filter_complex", ";".join(graph_parts), "-map", "[vout]"]
    if voice_path and music_path:
        command += ["-map", "[aout]"]
    elif voice_path:
        command += ["-map", "1:a:0"]
    elif music_path:
        command += ["-map", "2:a:0"]
    else:
        command += ["-map", "0:a:0?"]
    command += ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "fastdecode", "-threads", "0", "-crf", "27", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart"]
    if source_duration > 0:
        command += ["-t", f"{source_duration:.3f}"]
    command += [output_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Rendering timed out. Try a shorter video.") from exc
    if result.returncode != 0:
        raise ValueError(f"MP4 rendering failed: {result.stderr[-900:]}")
    output = Path(output_path)
    if not output.is_file() or output.stat().st_size < 1024:
        raise ValueError("FFmpeg finished without creating a valid MP4 output.")


def embed_preview_html(source: SourceInfo) -> str | None:
    if source.platform != "YouTube":
        return None
    parsed = urlparse(source.url)
    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    video_id = path_parts[-1] if host in {"youtu.be", "www.youtu.be"} and path_parts else ""
    if path_parts and path_parts[0] in {"shorts", "embed", "live"}:
        video_id = path_parts[1] if len(path_parts) > 1 else ""
    if parsed.query:
        video_id = parse_qs(parsed.query).get("v", [video_id])[0]
    if not video_id:
        return None
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", video_id)
    if not safe_id:
        return None
    return f'''<style>html,body{{margin:0;background:#090d1b;overflow:hidden}}iframe{{width:100%;height:380px;border:0;border-radius:18px;background:#10172b}}</style><iframe src="https://www.youtube-nocookie.com/embed/{safe_id}?rel=0" title="YouTube preview" allowfullscreen></iframe>'''


def preview_html(media_path: str, state: EditorState, final: bool = False) -> str:
    if not media_path or not Path(media_path).exists():
        return '<div class="empty-preview">Load a source video to see it here.</div>'
    encoded = base64.b64encode(Path(media_path).read_bytes()).decode("ascii")
    mime = "video/mp4" if media_path.lower().endswith(".mp4") else "video/webm"
    transform = "scaleX(-1)" if state.flip else "none"
    opacity = min(0.82, max(0.05, state.blur_strength / 115))
    blur_box = f"left:{state.blur_x}%;top:{state.blur_y}%;width:{state.blur_w}%;height:{state.blur_h}%;opacity:{opacity};"
    label = "FINAL RECAP PREVIEW" if final else "ORIGINAL SOURCE PREVIEW"
    return f"""
    <style>
      html,body{{margin:0;background:#090d1b;overflow:hidden}}
      .stage{{position:relative;height:380px;overflow:hidden;border:1px solid rgba(255,255,255,.16);border-radius:18px;background:#0f172b;display:grid;place-items:center}}
      video{{width:100%;height:100%;object-fit:contain;transform:{transform}}}
      .blurbox{{position:absolute;{blur_box}border:2px solid #70e8d8;background:rgba(112,232,216,.24);box-sizing:border-box;resize:both;overflow:auto;cursor:move}}
      .tag{{position:absolute;left:14px;top:12px;padding:7px 10px;border-radius:8px;background:rgba(5,8,18,.76);color:#f7f8ff;font:700 10px system-ui;letter-spacing:.12em}}
      .hint{{position:absolute;right:14px;bottom:12px;padding:6px 9px;border-radius:7px;background:rgba(5,8,18,.76);color:#b8c0d7;font:600 10px system-ui}}
      .empty-preview{{height:380px;display:grid;place-items:center;color:#c6cde0;background:#10172b;border-radius:18px;font:600 14px system-ui}}
    </style>
    <div class="stage"><video id="v" controls playsinline src="data:{mime};base64,{encoded}"></video><div class="blurbox"></div><div class="tag">{label}</div><div class="hint">{state.speed:.2f}× · {"FLIPPED" if state.flip else "NORMAL"}</div></div>
    <script>const v=document.getElementById('v');v.playbackRate={state.speed};</script>
    """
