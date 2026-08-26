import tempfile
import unittest
from pathlib import Path

from streamlit_app.audio import make_srt
from streamlit_app.config import FONT_PRESETS, EditorState
from streamlit_app.render import _subtitle_filter, _video_graph


class ReferenceStyleTests(unittest.TestCase):
    def test_ten_unicode_font_presets_are_exposed(self):
        self.assertEqual(len(FONT_PRESETS), 10)
        self.assertIn("Noto Sans Myanmar", FONT_PRESETS)
        self.assertIn("Padauk", FONT_PRESETS)

    def test_subtitle_filter_uses_selected_myanmar_font_and_yellow_outline(self):
        state = EditorState(subtitle_font="Noto Sans Myanmar SemiBold", subtitle_size=52, subtitle_position="Bottom")
        filt = _subtitle_filter("/tmp/captions.srt", state)
        self.assertIn("FontName=Noto Sans Myanmar SemiBold", filt)
        self.assertIn("PrimaryColour=&H0000FFFF", filt)
        self.assertIn("Outline=3", filt)
        self.assertIn("Alignment=2", filt)

    def test_blur_graph_is_region_only(self):
        state = EditorState(blur_strength=28, blur_x=5, blur_y=72, blur_w=90, blur_h=18)
        graph = _video_graph("/tmp/source.mp4", "/tmp/captions.srt", state, "9:16", 30)
        self.assertIn("crop=w=iw*0.9000:h=ih*0.1800", graph)
        self.assertIn("boxblur=14:2", graph)
        self.assertIn("overlay=x=main_w*0.0500:y=main_h*0.7200", graph)
        self.assertNotIn("[0:v]boxblur", graph)

    def test_srt_is_created_with_burmese_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.srt"
            make_srt({"recap_bn": "မြန်မာ ဇာတ်ကြောင်း", "subtitle_bn": "မြန်မာ စာတန်း"}, 10, str(path), mode="Burmese only")
            self.assertIn("မြန်မာ စာတန်း", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
