import ssl
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.dhflow.indextts import (
    EMOTION_ORDER,
    IndexTTS302,
    build_task_payload,
    emotion_alpha,
    emotion_vector,
    lossless_segments,
)
from scripts.dhflow.state import apply_auto_defaults, create_state, validate_state


SKILL_ROOT = Path(__file__).resolve().parents[1]


class IndexTTSRoutingTests(unittest.TestCase):
    def test_client_uses_an_explicit_verified_ssl_context(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b"{}"

        client = IndexTTS302("test-key")
        with patch(
            "scripts.dhflow.indextts.urllib.request.urlopen",
            return_value=FakeResponse(),
        ) as urlopen:
            self.assertEqual({}, client._read_json(object()))

        context = urlopen.call_args.kwargs.get("context")
        self.assertIsInstance(context, ssl.SSLContext)
        self.assertTrue(context.get_ca_certs())

    def test_skill_offers_indextts_as_a_third_voice_option(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        routing = (SKILL_ROOT / "references" / "voice-routing.md").read_text(
            encoding="utf-8"
        )
        question = "这次配音使用 MiniMax，HeyGen，还是 IndexTTS-2？"
        self.assertIn(question, skill)
        self.assertIn(question, routing)
        self.assertIn("`indextts`", skill)
        self.assertIn("IndexTTS-2 via 302.AI", routing)
        self.assertIn("MiniMax (recommended)", routing)

    def test_emotion_vector_is_one_hot_in_official_order(self):
        self.assertEqual(
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            emotion_vector("surprised"),
        )
        self.assertEqual(list(EMOTION_ORDER), [
            "happy",
            "angry",
            "sad",
            "afraid",
            "disgusted",
            "melancholic",
            "surprised",
            "calm",
        ])
        self.assertEqual(0.85, emotion_alpha(0.99))
        with self.assertRaisesRegex(ValueError, "unsupported IndexTTS emotion"):
            emotion_vector("shouting")

    def test_payload_maps_voice_plan_delivery_and_rejects_local_speaker_paths(self):
        payload = build_task_payload(
            "你好。",
            "https://example.com/voice.wav",
            {"emotion": "angry", "emotion_intensity": 0.82},
        )
        self.assertEqual("你好。", payload["text"])
        self.assertEqual([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], payload["emotion_vector"])
        self.assertEqual(0.82, payload["emotion_alpha"])
        with self.assertRaisesRegex(ValueError, "http"):
            build_task_payload("你好。", "/tmp/voice.wav", {"emotion": "calm", "emotion_intensity": 0.2})

    def test_payload_accepts_an_explicit_mixed_emotion_vector(self):
        vector = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9]
        payload = build_task_payload(
            "你好。",
            "https://example.com/voice.wav",
            {
                "emotion_vector": vector,
                "emotion": "calm",
                "emotion_intensity": 0.31,
            },
        )
        self.assertEqual(vector, payload["emotion_vector"])
        self.assertEqual(0.31, payload["emotion_alpha"])

    def test_payload_rejects_invalid_mixed_emotion_vectors(self):
        cases = (
            ([0.0] * 7, "eight numbers"),
            ([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.1, 1.1], "between 0 and 1"),
            ([0.1] * 8, "sum to 1"),
        )
        for vector, message in cases:
            with self.subTest(vector=vector):
                with self.assertRaisesRegex(ValueError, message):
                    build_task_payload(
                        "你好。",
                        "https://example.com/voice.wav",
                        {"emotion_vector": vector, "emotion_intensity": 0.2},
                    )

    def test_lossless_segments_reject_rewritten_text(self):
        plan = {
            "segments": [
                {"id": "a", "text": "你好。"},
                {"id": "b", "text": "继续。"},
            ]
        }
        self.assertEqual(2, len(lossless_segments(plan, "你好。继续。")))
        with self.assertRaisesRegex(ValueError, "lossless"):
            lossless_segments(plan, "你好，继续。")

    def test_state_accepts_indextts_and_auto_still_defaults_to_minimax(self):
        state = create_state(status="planned")
        state["assets"]["job_route"] = {
            "operating_mode": "interactive",
            "voice_provider": "indextts",
            "material_route": "none",
        }
        validate_state(state)
        auto = apply_auto_defaults(create_state(status="planned"))
        self.assertEqual("minimax", auto["assets"]["job_route"]["voice_provider"])

    def test_env_example_keeps_credentials_out_of_skill_docs(self):
        example = (SKILL_ROOT / ".env.example").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("INDEXTTS_302_API_KEY=", example)
        self.assertIn("INDEXTTS_SPEAKER_AUDIO_URL=", example)
        self.assertNotIn("INDEXTTS_302_API_KEY=sk-", skill)


if __name__ == "__main__":
    unittest.main()
