import json
import unittest

from scripts.dhflow.minimax import build_task_payload, director_intensity


class MiniMaxDirectorMappingTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "model": "speech-2.8-hd",
            "resolved_voice_id": "huangxu1",
        }

    def test_director_marker_is_translated_but_never_sent(self):
        segment = {
            "text": "所有事情就停了。",
            "emotion": "angry",
            "speed": 1.02,
            "director_intensity": 0.66,
        }
        payload = build_task_payload(self.plan, segment)
        serialized = json.dumps(payload)

        self.assertEqual(0.66, director_intensity(segment))
        self.assertEqual("angry", payload["voice_setting"]["emotion"])
        self.assertEqual(1.02, payload["voice_setting"]["speed"])
        self.assertNotIn("director_intensity", serialized)
        self.assertNotIn("emotion_intensity", serialized)

    def test_legacy_emotion_intensity_is_read_only_as_an_internal_marker(self):
        segment = {
            "text": "所有事情就停了。",
            "emotion": "angry",
            "speed": 1.02,
            "emotion_intensity": 0.66,
        }
        payload = build_task_payload(self.plan, segment)

        self.assertEqual(0.66, director_intensity(segment))
        self.assertNotIn("emotion_intensity", json.dumps(payload))

    def test_rejects_invalid_director_marker_and_provider_parameters(self):
        base = {
            "text": "所有事情就停了。",
            "emotion": "angry",
            "speed": 1.02,
            "director_intensity": 0.66,
        }
        for override, message in (
            ({"director_intensity": 0.86}, "director_intensity"),
            ({"emotion": "firm"}, "emotion"),
            ({"speed": 2.01}, "speed"),
        ):
            with self.subTest(override=override):
                with self.assertRaisesRegex(ValueError, message):
                    build_task_payload(self.plan, {**base, **override})


if __name__ == "__main__":
    unittest.main()
