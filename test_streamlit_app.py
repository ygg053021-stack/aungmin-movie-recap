import sys
import types
import unittest
from unittest.mock import patch

from streamlit_app import SourceInfo, embed_preview_html, inspect_source
from streamlit_app.media import download_authorized_source
from streamlit_app.transcript import fetch_public_transcript, youtube_video_id


class StreamlitLinkTests(unittest.TestCase):
    def test_youtube_shorts_embed_uses_video_id(self):
        source = inspect_source("https://youtube.com/shorts/pDDohu7oMPU?si=BN-hFh1hcagEGAVc")
        html = embed_preview_html(source)
        self.assertIsNotNone(html)
        self.assertIn("/embed/pDDohu7oMPU?rel=0", html)

    def test_non_youtube_provider_has_no_embed(self):
        source = SourceInfo("https://www.tiktok.com/@demo/video/1", "TikTok", "www.tiktok.com", "demo")
        self.assertIsNone(embed_preview_html(source))

    def test_youtube_video_id_supports_shorts_and_watch_links(self):
        self.assertEqual(youtube_video_id("https://youtube.com/shorts/pDDohu7oMPU?si=test"), "pDDohu7oMPU")
        self.assertEqual(youtube_video_id("https://www.youtube.com/watch?v=pDDohu7oMPU"), "pDDohu7oMPU")

    def test_public_transcript_uses_caption_text_without_video_download(self):
        class Snippet:
            def __init__(self, text):
                self.text = text

        class FakeTranscriptApi:
            def fetch(self, video_id, languages):
                self.video_id = video_id
                self.languages = languages
                return [Snippet("David can teleport."), Snippet("He discovers his power.")]

        fake_module = types.SimpleNamespace(YouTubeTranscriptApi=lambda: FakeTranscriptApi())
        with patch.dict(sys.modules, {"youtube_transcript_api": fake_module}):
            text = fetch_public_transcript("https://youtube.com/shorts/pDDohu7oMPU")
        self.assertEqual(text, "David can teleport.\nHe discovers his power.")

    def test_voiceover_writes_and_verifies_audio_file_without_path_symbol(self):
        import tempfile
        from pathlib import Path
        from streamlit_app.audio import create_voiceover

        seen = {}

        class FakeCommunicate:
            def __init__(self, text, _voice):
                seen["text"] = text

            async def save(self, path):
                Path(path).write_bytes(b"fake-audio-output" * 32)

        fake_module = types.SimpleNamespace(Communicate=FakeCommunicate)
        with tempfile.TemporaryDirectory() as workdir:
            output = f"{workdir}/voice.mp3"
            with patch.dict(sys.modules, {"edge_tts": fake_module}):
                script = "မြန်မာစာမူ " * 3000
                create_voiceover(script, output, "my-MM-NilarNeural")
            self.assertGreater(Path(output).stat().st_size, 0)
            self.assertEqual(seen["text"], script)

    def test_download_failure_is_reported_as_fallback_error(self):
        class FailingDownloader:
            def __init__(self, options):
                self.options = options

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def download(self, _urls):
                raise RuntimeError("HTTP Error 403: Forbidden")

        fake_module = types.SimpleNamespace(YoutubeDL=FailingDownloader)
        with patch.dict(sys.modules, {"yt_dlp": fake_module}):
            with self.assertRaisesRegex(ValueError, "Source could not be loaded"):
                download_authorized_source("https://youtube.com/shorts/pDDohu7oMPU")


if __name__ == "__main__":
    unittest.main()
