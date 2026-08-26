import unittest
from unittest.mock import patch

from streamlit_app import gemini


class FakeResponse:
    output_text = '{"recap_bn":"စမ်းသပ် recap","subtitle_bn":"စမ်းသပ်စာတန်း"}'


class FakeClient:
    class Interactions:
        def __init__(self):
            self.calls = []

        def create(self, model, input, generation_config):
            self.calls.append(model)
            if model == "gemini-2.5-flash":
                raise RuntimeError("503 UNAVAILABLE: model is experiencing high demand")
            return FakeResponse()

    def __init__(self):
        self.interactions = self.Interactions()


class GeminiRecoveryTests(unittest.TestCase):
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
        self.assertEqual(model, gemini.MODEL_NAME)
        self.assertEqual(response.output_text, FakeResponse.output_text)
        self.assertEqual(client.interactions.calls, ["gemini-2.5-flash"] * 3 + [gemini.MODEL_NAME])
        self.assertEqual(sleep.call_count, 2)

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
                    gemini.MODEL_CANDIDATES = ("gemini-2.5-flash", "gemini-2.5-flash")
                    gemini._retry_model_operation(
                        "test-key",
                        lambda current, selected: current.interactions.create(model=selected, input="test", generation_config={}),
                        "video analysis",
                    )
                finally:
                    gemini.MODEL_CANDIDATES = original


if __name__ == "__main__":
    unittest.main()
