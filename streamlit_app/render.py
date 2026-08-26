import base64
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import EditorState, SourceInfo

def render_mp4(source_path: str, srt_path: str, voice_path: str | None, output_path: str, effects: EditorState, ratio: str, music_path: str | None = None, target_width: int = 1920, target_height: int = 1080, target_fps: int = 30) -> None:
    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subtitle_path = srt_path.replace("\\", "/").replace(":", "\\:")
    source_duration = 0.0
    try:
        from .media import probe_duration
        source_duration = probe_duration(source_path)
    except Exception:
        source_duration = 0.0
    video_filters = [f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease", f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black", f"fps={target_fps}", f"subtitles='{subtitle_path}'"]
    if effects.blur_strength > 0:
        video_filters.append(f"boxblur={max(1, effects.blur_strength // 12)}:1")
    if effects.flip:
        video_filters.append("hflip")
    if ratio == "9:16":
        video_filters.append("crop=ih*9/16:ih")
    elif ratio == "1:1":
        video_filters.append("crop=ih:ih")
    if effects.speed != 1.0:
        video_filters.append(f"setpts=PTS/{effects.speed}")
    command = [ffmpeg, "-y", "-i", source_path]
    if voice_path:
        command += ["-i", voice_path]
    if music_path:
        command += ["-i", music_path]
    command += ["-vf", ",".join(video_filters), "-map", "0:v:0"]
    if voice_path and music_path:
        command += ["-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.18[music];[voice][music]amix=inputs=2:duration=shortest[aout]", "-map", "[aout]"]
    elif voice_path:
        command += ["-map", "1:a:0"]
    elif music_path:
        command += ["-map", "2:a:0"]
    else:
        command += ["-map", "0:a:0?"]
    command += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-c:a", "aac"]
    if source_duration > 0:
        command += ["-t", f"{source_duration:.3f}"]
    command += ["-movflags", "+faststart", output_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Rendering timed out. Try a shorter video.") from exc
    if result.returncode != 0:
        raise ValueError(f"MP4 rendering failed: {result.stderr[-700:]}")


def embed_preview_html(source: SourceInfo) -> str | None:
    """Return a browser preview for providers that expose an embed URL."""
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
