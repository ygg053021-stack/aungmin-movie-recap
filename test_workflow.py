import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit_app.config import EditorState
from streamlit_app import pipeline
from streamlit_app.audio import _atempo_chain, fit_audio_preserving_script
from streamlit_app.gemini import _validate_full_length_bundle
from streamlit_app.pipeline import apply_automatic_recap_defaults, run_one_click_recap


class WorkflowTests(unittest.TestCase):
    def test_atempo_chain_supports_longer_and_shorter_narration(self):
        self.assertEqual(_atempo_chain(1.0), "anull")
        self.assertIn("atempo=2.0", _atempo_chain(2.5))
        self.assertIn("atempo=0.5", _atempo_chain(0.25))

    def test_audio_fitting_does_not_silently_trim_long_approved_script(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "voice.mp3"
            source.write_bytes(b"voice")
            with patch("streamlit_app.media.probe_duration", return_value=12.0):
                with self.assertRaises(ValueError):
                    fit_audio_preserving_script(str(source), str(Path(root) / "fitted.mp3"), 10.0, max_speed_delta=0.1)

    def test_one_click_transaction_generates_voice_applies_defaults_and_renders(self):
        editor = EditorState()
        bundle = {"recap_bn": "full recap", "segments": [{"start": 0, "end": 20, "text": "full", "text_en": "full"}]}
        voice = {"voice_bytes": b"approved voice", "voice_path": "/tmp/approved.mp3"}
        with patch("streamlit_app.gemini.generate_recap_bundle", return_value=bundle) as generate, patch.object(pipeline, "render_voice_preview", return_value=voice) as preview, patch.object(pipeline, "render_bundle_to_mp4", return_value=b"\\x00\\x00\\x00final") as render:
            result_bundle, result_voice, result_video = run_one_click_recap("key", object(), "/tmp/source.mp4", editor)
        self.assertIs(result_bundle, bundle)
        self.assertIs(result_voice, voice)
        self.assertEqual(result_video, b"\\x00\\x00\\x00final")
        self.assertTrue(editor.subtitle_enabled)
        self.assertTrue(editor.blur_enabled)
        generate.assert_called_once()
        preview.assert_called_once()
        render.assert_called_once()

    def test_one_click_defaults_enable_bilingual_subtitle_and_blur(self):
        editor = apply_automatic_recap_defaults(EditorState())
        self.assertTrue(editor.subtitle_enabled)
        self.assertEqual(editor.subtitle_mode, "Burmese + English")
        self.assertTrue(editor.blur_enabled)
        self.assertEqual((editor.blur_x, editor.blur_y, editor.blur_w, editor.blur_h), (0, 68, 100, 32))
        self.assertEqual(editor.subtitle_fill, "#FFF200")

    def test_short_recap_bundle_is_rejected_before_tts(self):
        with self.assertRaisesRegex(ValueError, "တိုလွန်း"):
            _validate_full_length_bundle(
                {
                    "recap_bn": "တိုတောင်းသော recap",
                    "segments": [{"start": 0, "end": 60, "text": "တိုတောင်းသော recap", "text_en": "A short recap"}],
                },
                60.0,
            )

    def test_full_length_bundle_requires_scene_coverage(self):
        bundle = {
            "recap_bn": "က" * 650,
            "segments": [
                {"start": 0, "end": 20, "text": "က" * 120, "text_en": "A"},
                {"start": 20, "end": 40, "text": "က" * 120, "text_en": "B"},
                {"start": 40, "end": 55, "text": "က" * 120, "text_en": "C"},
                {"start": 55, "end": 60, "text": "က" * 120, "text_en": "D"},
            ],
        }
        _validate_full_length_bundle(bundle, 60.0)

    def test_final_render_copies_approved_voice_without_regenerating(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            media = root_path / "source.mp4"
            approved = root_path / "approved.mp3"
            media.write_bytes(b"source")
            approved.write_bytes(b"approved voice" * 100)
            output = root_path / "final.mp4"
            seen = {}

            def fake_probe(path):
                if str(path).endswith("source.mp4"):
                    return 10.0
                return 4.0

            def fake_render(media_path, srt_path, voice_path, output_path, editor, ratio, music_path=None, logo_path=None):
                seen["voice"] = Path(voice_path).read_bytes()
                Path(output_path).write_bytes(b"\x00\x00\x00approved-final" + b"x" * 2048)

            def fake_fit(input_path, output_path, target_seconds):
                Path(output_path).write_bytes(Path(input_path).read_bytes())
                return target_seconds

            with patch.object(pipeline, "probe_duration", side_effect=fake_probe), patch.object(pipeline, "fit_audio_preserving_script", side_effect=fake_fit), patch.object(pipeline, "render_mp4", side_effect=fake_render), patch.object(pipeline, "create_voiceover", side_effect=AssertionError("approved voice must not be regenerated")):
                result = pipeline.render_bundle_to_mp4(
                    str(media),
                    {"recap_bn": "မြန်မာ recap", "subtitle_bn": "စာတန်း"},
                    "my-MM-ThihaNeural",
                    EditorState(),
                    "TikTok",
                    approved_voice_path=str(approved),
                )
            self.assertTrue(result.startswith(b"\x00\x00\x00"))
            self.assertEqual(seen["voice"], b"approved voice" * 100)


if __name__ == "__main__":
    unittest.main()
