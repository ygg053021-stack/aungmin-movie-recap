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

    def test_bundle_parser_preserves_chronological_scene_segments(self):
        text = '{"recap_bn":"အစမှအဆုံး recap","subtitle_bn":"စာတန်း","segments":[{"start":4,"end":10,"text":"ဒုတိယ scene"},{"start":0,"end":4,"text":"ပထမ scene"},{"start":12,"end":30,"text":"ကန့်သတ်ပြီးနောက် scene"}]}'
        bundle = gemini._parse_bundle(text, duration=15)
        self.assertEqual([segment["text"] for segment in bundle["segments"]], ["ပထမ scene", "ဒုတိယ scene", "ကန့်သတ်ပြီးနောက် scene"])
        self.assertEqual(bundle["segments"][-1]["end"], 15.0)

    def test_bundle_parser_normalizes_scene_windows_to_one_gap_free_timeline(self):
        text = '{"recap_bn":"အ" * 400,"subtitle_bn":"စာတန်း","segments":[{"start":5,"end":12,"text":"ပထမ","text_en":"First"},{"start":10,"end":18,"text":"ဒုတိယ","text_en":"Second"},{"start":22,"end":25,"text":"တတိယ","text_en":"Third"}]}'
        text = text.replace('"အ" * 400', '"' + ('အ' * 400) + '"')
        bundle = gemini._parse_bundle(text, duration=30)
        segments = bundle["segments"]
        self.assertEqual(segments[0]["start"], 0.0)
        self.assertEqual(segments[-1]["end"], 30.0)
        self.assertTrue(all(segments[i]["end"] <= segments[i + 1]["start"] for i in range(len(segments) - 1)))
        self.assertEqual(segments[1]["start"], segments[0]["end"])

    def test_bundle_parser_accepts_sdk_output_text(self):
        bundle = gemini._parse_bundle(FakeResponse.output_text)
        self.assertEqual(bundle["recap_bn"], "စမ်းသပ် recap")
        self.assertEqual(bundle["subtitle_bn"], "စမ်းသပ်စာတန်း")

    def test_full_length_bundle_rejects_missing_english_scene_translation(self):
        with self.assertRaisesRegex(ValueError, "English subtitle translation"):
            gemini._validate_full_length_bundle(
                {
                    "recap_bn": "က" * 900,
                    "segments": [{"start": 0, "end": 15, "text": "scene", "text_en": "Scene"}, {"start": 15, "end": 30, "text": "scene 2", "text_en": "Scene 2"}, {"start": 30, "end": 45, "text": "scene 3", "text_en": "Scene 3"}, {"start": 45, "end": 60, "text": "scene 4"}],
                },
                60.0,
            )

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
