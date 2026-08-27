from pathlib import Path
from tempfile import TemporaryDirectory

from streamlit_app.audio import make_srt, stamp
from streamlit_app.config import EditorState
from streamlit_app.editor import canvas_initial_drawing
from streamlit_app.render import _subtitle_filter


def test_auto_srt_compacts_long_burmese_text_to_narration_duration():
    bundle = {"subtitle_bn": "ဒီမြင်ကွင်းမှာ ဇာတ်ကောင်က အဆောက်အဦးရှေ့မှာ တစ်ယောက်တည်း ရပ်နေပြီး အရေးကြီးတဲ့ အဖြစ်အပျက်ကို စောင့်နေပါတယ်"}
    with TemporaryDirectory() as directory:
        path = Path(directory) / "captions.srt"
        make_srt(bundle, 42.333, str(path), 0.0, "Burmese only")
        text = path.read_text(encoding="utf-8")
        assert "-->" in text
        caption_lines = [line for line in text.splitlines() if line and not line.isdigit() and "-->" not in line]
        assert all(len(line) <= 24 for line in caption_lines)


def test_srt_preserves_long_approved_text_and_millisecond_timestamps():
    marker = "အဆုံးထိမဖြတ်ရမည့်အတည်ပြုစာသား"
    bundle = {"subtitle_bn": "အစ " + ("မြန်မာစာ " * 90) + marker}
    with TemporaryDirectory() as directory:
        path = Path(directory) / "captions.srt"
        make_srt(bundle, 42.333, str(path), 0.0, "Burmese only")
        text = path.read_text(encoding="utf-8")
        assert marker in text
        assert stamp(1.234) == "00:00:01,234"
        assert "00:00:00,000 --> 00:00:42,333" in text


def test_portrait_canvas_and_selected_design_reach_preview_and_render():
    state = EditorState(subtitle_fill="#63F5FF", subtitle_outline="#FFFFFF", subtitle_background_opacity=72, subtitle_x=20, subtitle_w=50)
    drawing = canvas_initial_drawing(state, 405, 720, "မြန်မာစာတန်း", "Pyidaungsu Book")
    subtitle = next(obj for obj in drawing["objects"] if obj.get("name") == "subtitle")
    assert subtitle["fill"] == "#63F5FF"
    assert subtitle["fontSize"] < 42
    filter_graph = _subtitle_filter("/tmp/captions.srt", state)
    assert "PrimaryColour=&H00FFF563" in filter_graph
    assert "BorderStyle=3" in filter_graph
    assert "MarginL=384" in filter_graph
    assert "MarginR=576" in filter_graph
    assert subtitle["left"] == 405 * 0.20
    assert subtitle["width"] == 405 * 0.50
