from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import EditorState


def extract_preview_frame(media_path: str, width: int = 720, height: int = 405):
    """Extract a first-frame PIL image for direct on-screen editing."""
    from io import BytesIO
    import imageio_ffmpeg
    from PIL import Image

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", "0", "-i", media_path,
        "-frames:v", "1", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, timeout=30)
    if result.returncode != 0 or not result.stdout:
        raise ValueError("Video frame preview ကို မဖန်တီးနိုင်ပါ။")
    return Image.open(BytesIO(result.stdout)).convert("RGBA")


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
    text = subtitle.strip()[:120]
    box = draw.multiline_textbbox((0, 0), text, font=font, stroke_width=2, spacing=4, align="center")
    text_w, text_h = box[2] - box[0], box[3] - box[1]
    x = max(8, (image.width - text_w) // 2)
    y = {"Top": 28, "Center": (image.height - text_h) // 2, "Bottom": image.height - text_h - 30}.get(position, image.height - text_h - 30)
    draw.multiline_text((x, y), text, font=font, fill="#fff000", stroke_width=2, stroke_fill="#000000", spacing=4, align="center")
    return image


def canvas_initial_drawing(state: EditorState, width: int, height: int, subtitle: str = "", font_family: str = "sans-serif") -> dict:
    x, y = state.blur_x * width / 100, state.blur_y * height / 100
    w, h = state.blur_w * width / 100, state.blur_h * height / 100
    objects = [{
        "type": "rect", "left": x, "top": y, "width": w, "height": h,
        "fill": "rgba(0,0,0,0.58)", "stroke": "#70e8d8", "strokeWidth": 3,
        "selectable": True, "hasControls": True, "lockRotation": True,
    }]
    if subtitle.strip():
        objects.append({
            "type": "i-text", "left": width * 0.08, "top": height * 0.78,
            "text": subtitle[:120], "fontSize": max(18, min(54, int(state.subtitle_size * height / 1080))),
            "fontFamily": font_family or "sans-serif", "fill": "#fff000", "stroke": "#000000", "strokeWidth": 1,
            "paintFirst": "stroke", "selectable": True, "evented": True, "hasControls": True,
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
