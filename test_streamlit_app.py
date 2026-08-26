import sys
import types
import unittest
from unittest.mock import patch

from streamlit_app import SourceInfo, embed_preview_html, inspect_source
from streamlit_app.media import download_authorized_source


class StreamlitLinkTests(unittest.TestCase):
    def test_youtube_shorts_embed_uses_video_id(self):
        source = inspect_source("https://youtube.com/shorts/pDDohu7oMPU?si=BN-hFh1hcagEGAVc")
        html = embed_preview_html(source)
        self.assertIsNotNone(html)
        self.assertIn("/embed/pDDohu7oMPU?rel=0", html)

    def test_non_youtube_provider_has_no_embed(self):
        source = SourceInfo("https://www.tiktok.com/@demo/video/1", "TikTok", "www.tiktok.com", "demo")
        self.assertIsNone(embed_preview_html(source))

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
