import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit_app import gemini


class FakeResponse:
    output_text = '{"recap_bn":"စမ်းသပ် recap","subtitle_bn":"စမ်းသပ်စာတန်း"}'


class FakeUpload:
    uri = "https://generativelanguage.googleapis.com/v1beta/files/test"
    name = "files/test"
    mime_type = "video/mp4"
    state = "ACTIVE"


class FakeFiles:
    def __init__(self):
        self.upload_clients = []

    def upload(self, file):
        self.upload_clients.append(file)
        return FakeUpload()

    def get(self, name):
        return FakeUpload()


class FakeClient:
    class Interactions:
        def __init__(self):
            self.calls = []

        def create(self, model, input, generation_config):
            self.calls.append(model)
            if model == "gemini-3.6-flash":
                raise RuntimeError("503 UNAVAILABLE: model is experiencing high demand")
            return FakeResponse()

    def __init__(self):
        self.interactions = self.Interactions()
        self.files = FakeFiles()


class GeminiRecoveryTests(unittest.TestCase):
    def test_upload_uses_the_explicit_live_client(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as media:
            client = FakeClient()
            with patch.object(gemini, "_get_client", side_effect=AssertionError("temporary client must not be created")):
                uploaded = gemini.upload_to_gemini("test-key", media.name, client)
        self.assertEqual(uploaded.uri, FakeUpload.uri)
        self.assertEqual(client.files.upload_clients, [media.name])

    def test_503_retries_then_falls_back_to_reference_model(self):
        client = FakeClient()
        with patch.object(gemini, "_get_client", return_value=client), patch.object(gemini.time, "sleep") as sleep:
            response, model = gemini._retry_model_operation(
                "test-key",
                lambda current, selected: current.interactions.create(
                    model=selected,
                    input="test",
                    generation_config={},
                ),
                "video analysis",
            )
        self.assertEqual(model, "gemini-3.5-flash-lite")
        self.assertEqual(response.output_text, FakeResponse.output_text)
        self.assertEqual(client.interactions.calls, ["gemini-3.6-flash"] * 3 + ["gemini-3.5-flash-lite"])
        self.assertEqual(sleep.call_count, 2)

    def test_quota_error_skips_retries_and_uses_next_model(self):
        client = FakeClient()
        calls = []
        def quota_then_success(current, selected):
            calls.append(selected)
            if selected == "gemini-3.6-flash":
                raise RuntimeError("429 RESOURCE_EXHAUSTED: You exceeded your current quota")
            return FakeResponse()
        with patch.object(gemini, "_get_client", return_value=client), patch.object(gemini.time, "sleep") as sleep:
            response, model = gemini._retry_model_operation("test-key", quota_then_success, "video analysis")
        self.assertEqual(model, "gemini-3.5-flash-lite")
        self.assertEqual(calls, ["gemini-3.6-flash", "gemini-3.5-flash-lite"])
        sleep.assert_not_called()
        self.assertEqual(response.output_text, FakeResponse.output_text)

    def test_bundle_parser_accepts_sdk_output_text(self):
        bundle = gemini._parse_bundle(FakeResponse.output_text)
        self.assertEqual(bundle["recap_bn"], "စမ်းသပ် recap")
        self.assertEqual(bundle["subtitle_bn"], "စမ်းသပ်စာတန်း")

    def test_503_summary_is_actionable(self):
        client = FakeClient()
        with patch.object(gemini, "_get_client", return_value=client), patch.object(gemini.time, "sleep"):
            with self.assertRaisesRegex(ValueError, "503 retry နှင့် fallback model"):
                original = gemini.MODEL_CANDIDATES
                try:
                    gemini.MODEL_CANDIDATES = ("gemini-3.6-flash", "gemini-3.6-flash")
                    gemini._retry_model_operation(
                        "test-key",
                        lambda current, selected: current.interactions.create(model=selected, input="test", generation_config={}),
                        "video analysis",
                    )
                finally:
                    gemini.MODEL_CANDIDATES = original


if __name__ == "__main__":
    unittest.main()
