from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import EditorState


def extract_preview_frame(media_path: str, width: int = 720, height: int = 405, timestamp: float = 0.0):
    """Extract the selected source-video frame for direct on-screen editing."""
    from io import BytesIO
    import imageio_ffmpeg
    from PIL import Image

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    seek = max(0.0, float(timestamp or 0.0))
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{seek:.3f}", "-i", media_path,
        "-frames:v", "1", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, timeout=30)
    if result.returncode != 0 or not result.stdout:
        raise ValueError("Video frame preview ကို မဖန်တီးနိုင်ပါ။")
    return Image.open(BytesIO(result.stdout)).convert("RGBA")


def _wrap_preview_text(draw, text: str, font, max_width: int) -> str:
    compact = " ".join(str(text or "").replace("\n", " ").split())
    if not compact:
        return ""
    chunks = compact.split(" ") if " " in compact else list(compact)
    lines: list[str] = []
    current = ""
    for chunk in chunks:
        candidate = f"{current} {chunk}".strip() if " " in compact else current + chunk
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > max_width:
            lines.append(current.strip())
            current = chunk
        else:
            current = candidate
    if current:
        lines.append(current.strip())
    return "\n".join(lines[:3])


def add_preview_subtitle(frame, subtitle: str, font_path: str | None, size: int, position: str = "Bottom"):
    if not subtitle.strip():
        return frame
    from PIL import ImageDraw, ImageFont
    image = frame.copy().convert("RGBA")
    try:
        font = ImageFont.truetype(font_path, max(18, min(72, int(size * image.height / 1080)))) if font_path and Path(font_path).is_file() else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(image)
    text = _wrap_preview_text(draw, subtitle.strip()[:160], font, int(image.width * 0.86))
    box = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=2, spacing=4, align="center")
    text_w, text_h = box[2] - box[0], box[3] - box[1]
    x = max(8, (image.width - text_w) // 2)
    y = {"Top": 28, "Center": (image.height - text_h) // 2, "Bottom": image.height - text_h - 30}.get(position, image.height - text_h - 30)
    draw.multiline_text((x, y), text, font=font, fill="#fff000", stroke_width=2, stroke_fill="#000000", spacing=4, align="center")
    return image


def _compact_canvas_text(text: str, max_chars: int) -> str:
    compact = " ".join(str(text or "").replace("\n", " ").split())
    if len(compact) <= max_chars:
        return compact
    chunks = compact.split(" ") if " " in compact else list(compact)
    lines: list[str] = []
    current = ""
    for chunk in chunks:
        candidate = f"{current} {chunk}".strip() if " " in compact else current + chunk
        if current and len(candidate) > max_chars:
            lines.append(current.strip())
            current = chunk
        else:
            current = candidate
    if current:
        lines.append(current.strip())
    return "\n".join(lines[:3])


def canvas_initial_drawing(state: EditorState, width: int, height: int, subtitle: str = "", font_family: str = "sans-serif", logo_path: str | None = None) -> dict:
    x, y = state.blur_x * width / 100, state.blur_y * height / 100
    w, h = state.blur_w * width / 100, state.blur_h * height / 100
    objects = []
    if getattr(state, "blur_enabled", state.blur_strength > 0) and state.blur_strength > 0:
        objects.append({
            "type": "rect", "name": "blur", "left": x, "top": y, "width": w, "height": h,
            "fill": "rgba(0,0,0,0.58)", "stroke": "#70e8d8", "strokeWidth": 3,
            "selectable": True, "hasControls": True, "lockRotation": True,
        })
    if getattr(state, "subtitle_enabled", True) and subtitle.strip():
        font_size = max(16, min(42, int(state.subtitle_size * min(width / 1920, height / 1080) * 1.35)))
        max_chars = max(10, min(24, int(width / max(font_size * 0.58, 1))))
        subtitle_text = _compact_canvas_text(subtitle[:180], max_chars)
        objects.append({
            "type": "i-text", "name": "subtitle", "left": width * 0.08, "top": height * state.subtitle_y / 100,
            "width": width * 0.84, "text": subtitle_text, "fontSize": font_size,
            "fontFamily": font_family or "sans-serif", "fill": getattr(state, "subtitle_fill", "#FFF200"), "stroke": getattr(state, "subtitle_outline", "#000000"), "strokeWidth": 1,
            "backgroundColor": getattr(state, "subtitle_background", "#000000") if getattr(state, "subtitle_background_opacity", 0) > 0 else "transparent",
            "textAlign": "center", "paintFirst": "stroke", "selectable": True, "evented": True, "hasControls": True,
        })
    if getattr(state, "watermark_text", "").strip():
        objects.append({
            "type": "i-text", "name": "watermark", "left": width * state.watermark_x / 100, "top": height * state.watermark_y / 100,
            "text": state.watermark_text[:80], "fontSize": max(12, min(42, int(state.watermark_size * height / 1080))),
            "fontFamily": font_family or "sans-serif", "fill": "#ffffff", "opacity": 0.72,
            "selectable": True, "evented": True, "hasControls": True,
        })
    if logo_path and Path(logo_path).is_file():
        import base64
        suffix = Path(logo_path).suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        encoded = base64.b64encode(Path(logo_path).read_bytes()).decode("ascii")
        objects.append({
            "type": "image", "name": "logo", "src": f"data:{mime};base64,{encoded}",
            "left": width * state.logo_x / 100, "top": height * state.logo_y / 100,
            "width": max(40, width * state.logo_w / 100), "height": max(40, width * state.logo_w / 100 * 0.6),
            "scaleX": 1, "scaleY": 1, "selectable": True, "evented": True, "hasControls": True,
        })
    return {"version": "5.3.0", "objects": objects}


def sync_blur_from_canvas(state: EditorState, json_data: str | None, width: int, height: int) -> tuple[EditorState, tuple[int, int, int, int] | None]:
    if not json_data:
        return state, None
    try:
        objects = json.loads(json_data).get("objects", [])
    except (TypeError, ValueError):
        return state, None
    rect = next((obj for obj in objects if obj.get("type") == "rect"), None)
    if not rect:
        return state, None
    left = max(0, min(width, float(rect.get("left", 0))))
    top = max(0, min(height, float(rect.get("top", 0))))
    rect_width = max(8, min(width - left, float(rect.get("width", width * .9)) * float(rect.get("scaleX", 1))))
    rect_height = max(8, min(height - top, float(rect.get("height", height * .18)) * float(rect.get("scaleY", 1))))
    coords = (round(left * 100 / width), round(top * 100 / height), round(rect_width * 100 / width), round(rect_height * 100 / height))
    state.blur_x, state.blur_y, state.blur_w, state.blur_h = coords
    return state, coords


def sync_overlays_from_canvas(state: EditorState, json_data: str | None, width: int, height: int) -> EditorState:
    """Persist draggable subtitle, watermark, and logo geometry from the canvas."""
    if not json_data:
        return state
    try:
        objects = json.loads(json_data).get("objects", [])
    except (TypeError, ValueError):
        return state
    for obj in objects:
        name = obj.get("name")
        left = max(0.0, min(width, float(obj.get("left", 0))))
        top = max(0.0, min(height, float(obj.get("top", 0))))
        scale_x = float(obj.get("scaleX", 1) or 1)
        scale_y = float(obj.get("scaleY", 1) or 1)
        obj_width = max(1.0, float(obj.get("width", 1)) * scale_x)
        obj_height = max(1.0, float(obj.get("height", 1)) * scale_y)
        if name == "subtitle":
            state.subtitle_x = round(left * 100 / width)
            state.subtitle_y = round(top * 100 / height)
            state.subtitle_w = max(5, min(100, round(obj_width * 100 / width)))
            state.subtitle_h = max(5, min(80, round(obj_height * 100 / height)))
            state.subtitle_size = max(18, min(96, round(float(obj.get("fontSize", state.subtitle_size)) * 1080 / height)))
        elif name == "watermark":
            state.watermark_x = round(left * 100 / width)
            state.watermark_y = round(top * 100 / height)
            state.watermark_size = max(12, min(72, round(float(obj.get("fontSize", state.watermark_size)) * 1080 / height)))
        elif name == "logo":
            state.logo_x = round(left * 100 / width)
            state.logo_y = round(top * 100 / height)
            state.logo_w = max(5, min(60, round(obj_width * 100 / width)))
    return state
