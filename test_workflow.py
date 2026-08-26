import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit_app.config import EditorState
from streamlit_app import pipeline


class WorkflowTests(unittest.TestCase):
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

            with patch.object(pipeline, "probe_duration", side_effect=fake_probe), patch.object(pipeline, "render_mp4", side_effect=fake_render), patch.object(pipeline, "create_voiceover", side_effect=AssertionError("approved voice must not be regenerated")):
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
