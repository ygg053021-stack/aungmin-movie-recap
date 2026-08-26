import tempfile
import unittest
from pathlib import Path

from streamlit_app.audio import make_srt
from streamlit_app.config import FONT_PRESETS, EditorState
from streamlit_app.render import _subtitle_filter, _video_graph
from streamlit_app.editor import add_preview_subtitle, canvas_initial_drawing, sync_blur_from_canvas


class ReferenceStyleTests(unittest.TestCase):
    def test_ten_unicode_font_presets_are_exposed(self):
        self.assertEqual(len(FONT_PRESETS), 11)
        self.assertIn("Pyidaungsu Book Regular", FONT_PRESETS)
        self.assertIn("OT43 YellYint Thin", FONT_PRESETS)
        self.assertIn("Z10 Cartoon", FONT_PRESETS)

    def test_subtitle_filter_uses_selected_myanmar_font_and_yellow_outline(self):
        state = EditorState(subtitle_font="Pyidaungsu Book Regular", subtitle_size=52, subtitle_position="Bottom")
        filt = _subtitle_filter("/tmp/captions.srt", state)
        self.assertIn("FontName=Pyidaungsu Book", filt)
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

    def test_voice_preview_graph_skips_missing_srt(self):
        state = EditorState(blur_strength=0)
        graph = _video_graph("/tmp/source.mp4", None, state, "9:16", 30)
        self.assertNotIn("subtitles=", graph)
        self.assertIn("scale=1080:1920", graph)

    def test_supplied_ttf_files_exist_and_preview_subtitle_is_rendered(self):
        font_dir = Path(__file__).parent / "fonts"
        self.assertTrue((font_dir / "Pyidaungsu-Book-Regular.ttf").is_file())
        from PIL import Image
        frame = Image.new("RGBA", (720, 405), "black")
        rendered = add_preview_subtitle(frame, "မြန်မာ စာတန်း", str(font_dir / "Pyidaungsu-Book-Regular.ttf"), 52)
        self.assertEqual(rendered.size, (720, 405))
        self.assertNotEqual(rendered.tobytes(), frame.tobytes())

    def test_dragged_blur_coordinates_sync_to_editor_state(self):
        state = EditorState()
        drawing = canvas_initial_drawing(state, 720, 405, "မြန်မာစာတန်း", "Pyidaungsu Book")
        drawing["objects"][0].update({"left": 144, "top": 243, "width": 360, "height": 81})
        state, coords = sync_blur_from_canvas(state, __import__("json").dumps(drawing), 720, 405)
        self.assertEqual(coords, (20, 60, 50, 20))
        self.assertEqual((state.blur_x, state.blur_y, state.blur_w, state.blur_h), coords)

    def test_srt_is_created_with_burmese_text(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "captions.srt"
            make_srt({"recap_bn": "မြန်မာ ဇာတ်ကြောင်း", "subtitle_bn": "မြန်မာ စာတန်း"}, 10, str(path), mode="Burmese only")
            self.assertIn("မြန်မာ စာတန်း", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
