import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class PerformancePrimitiveTests(unittest.TestCase):
    def test_plan_uses_versioned_legal_primitive_chains(self):
        from scripts.dhflow.content_director import analyze_script
        from scripts.dhflow.performance_director import plan_performance

        plan = plan_performance(
            analyze_script("为什么动作会显得僵硬？因为手势不能脱离整个人。现在就修正。"),
            hand_topology="separated",
        )

        library = plan["primitive_library"]
        self.assertEqual("business-human-performance-primitives-v1", library["id"])
        self.assertEqual(
            "references/performance-primitives.json", library["source"]
        )
        self.assertRegex(library["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual("semantic_relative_only", library["provider_timing_contract"])

        for beat in plan["beats"]:
            chain = beat["primitive_chain"]
            self.assertEqual("living_idle", chain[0])
            self.assertEqual("phrase_settle", chain[-1])
            self.assertEqual(len(chain), len(set(chain)))
            self.assertIn("brow_lead", chain)
            self.assertIn("head_accent", chain)
            self.assertIn("neck_shoulder_absorb", chain)
            self.assertIn("torso_counterweight", chain)
            if beat["hands"]["enabled"]:
                self.assertIn("hand_stroke", chain)
            else:
                self.assertNotIn("hand_stroke", chain)

    def test_primitive_library_is_bound_to_123_and_forbids_timeline_copy(self):
        path = SKILL_ROOT / "references" / "performance-primitives.json"
        data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(1, data["schema_version"])
        self.assertEqual("business-human-123-v1", data["reference_id"])
        self.assertEqual("performance_only", data["scope"])
        self.assertFalse(data["provider_contract"]["frame_accurate_timing_claimed"])
        self.assertTrue(data["provider_contract"]["exact_reference_timeline_copy_forbidden"])
        primitive_ids = [item["id"] for item in data["primitives"]]
        self.assertEqual(len(primitive_ids), len(set(primitive_ids)))
        self.assertTrue(
            {
                "living_idle",
                "gaze_return",
                "brow_lead",
                "head_accent",
                "neck_shoulder_absorb",
                "torso_counterweight",
                "hand_stroke",
                "phrase_settle",
            }.issubset(primitive_ids)
        )


class PerformanceBeatMapTests(unittest.TestCase):
    def _plans(self):
        from scripts.dhflow.content_director import analyze_script
        from scripts.dhflow.performance_director import plan_performance
        from scripts.dhflow.voice_director import plan_voice

        beats = analyze_script("为什么会僵硬？因为手势脱离了身体。现在就修正。")
        return plan_voice(beats, "boss"), plan_performance(beats, "separated")

    def test_beat_map_binds_exact_audio_and_uses_times_only_for_planning_and_qa(self):
        from scripts.dhflow.performance_timing import build_performance_beat_map

        voice_plan, performance_plan = self._plans()
        audio_sha256 = "a" * 64
        timing = {
            "segments": [
                {
                    "id": segment["id"],
                    "text": segment["text"],
                    "start_seconds": start,
                    "end_seconds": end,
                }
                for segment, start, end in zip(
                    voice_plan["segments"],
                    (0.0, 1.6, 4.2),
                    (1.6, 4.2, 6.1),
                    strict=True,
                )
            ]
        }

        result = build_performance_beat_map(
            voice_plan=voice_plan,
            performance_plan=performance_plan,
            timing_document=timing,
            audio_sha256=audio_sha256,
            audio_duration_seconds=6.1,
        )

        self.assertEqual(audio_sha256, result["audio"]["sha256"])
        self.assertEqual(6.1, result["audio"]["duration_seconds"])
        self.assertEqual("planning_and_rendered_qa_only", result["timing_scope"])
        self.assertFalse(result["provider_frame_accurate_timing_claimed"])
        self.assertTrue(result["exact_reference_timeline_copy_forbidden"])
        self.assertEqual(
            [item["id"] for item in voice_plan["segments"]],
            [item["id"] for item in result["beats"]],
        )
        self.assertEqual(0.0, result["beats"][0]["start_seconds"])
        self.assertEqual(6.1, result["beats"][-1]["end_seconds"])
        for beat in result["beats"]:
            self.assertEqual(3, len(beat["qa_checkpoints"]))
            self.assertEqual(
                ["entry", "readable_hold", "settle"],
                [checkpoint["phase"] for checkpoint in beat["qa_checkpoints"]],
            )

    def test_beat_map_rejects_text_or_audio_mismatch(self):
        from scripts.dhflow.performance_timing import build_performance_beat_map

        voice_plan, performance_plan = self._plans()
        timing = {
            "segments": [
                {
                    "id": segment["id"],
                    "text": segment["text"],
                    "start_seconds": index,
                    "end_seconds": index + 1,
                }
                for index, segment in enumerate(voice_plan["segments"])
            ]
        }
        timing["segments"][1]["text"] = "被改过的文案。"

        with self.assertRaisesRegex(ValueError, "exact text"):
            build_performance_beat_map(
                voice_plan=voice_plan,
                performance_plan=performance_plan,
                timing_document=timing,
                audio_sha256="b" * 64,
                audio_duration_seconds=3.0,
            )

    def test_beat_map_cli_binds_the_real_audio_file(self):
        voice_plan, performance_plan = self._plans()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            voice_path = root / "voice-plan.json"
            performance_path = root / "performance-plan.json"
            timings_path = root / "final-audio-segments.json"
            audio_path = root / "final.wav"
            output_path = root / "performance-beat-map.json"
            voice_path.write_text(json.dumps(voice_plan), encoding="utf-8")
            performance_path.write_text(
                json.dumps(performance_plan), encoding="utf-8"
            )
            timings_path.write_text(
                json.dumps(
                    {
                        "source": "test_exact_segment_boundaries",
                        "segments": [
                            {
                                "id": segment["id"],
                                "text": segment["text"],
                                "start_seconds": index,
                                "end_seconds": index + 1,
                            }
                            for index, segment in enumerate(voice_plan["segments"])
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with wave.open(str(audio_path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\0\0" * (8000 * len(voice_plan["segments"])))

            result = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "build_performance_beat_map.py"),
                    "--voice-plan",
                    str(voice_path),
                    "--performance-plan",
                    str(performance_path),
                    "--timings",
                    str(timings_path),
                    "--audio",
                    str(audio_path),
                    "--out",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            mapped = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                mapped["audio"]["sha256"],
            )


class PerformanceQcTests(unittest.TestCase):
    def test_relationship_comparison_rejects_hand_led_disconnection_without_pixels(self):
        from scripts.dhflow.performance_qc import compare_performance_features

        reference = {
            "motion": {
                "upper_face_to_mouth": 0.72,
                "head_to_hands": 0.42,
                "shoulders_to_hands": 0.58,
                "torso_to_hands": 0.46,
                "isolated_hand_rate": 0.08,
                "nonmouth_freeze_ratio": 0.06,
                "periodicity_peak": 0.18,
            }
        }
        candidate = {
            "motion": {
                "upper_face_to_mouth": 0.22,
                "head_to_hands": 0.11,
                "shoulders_to_hands": 0.13,
                "torso_to_hands": 0.09,
                "isolated_hand_rate": 0.61,
                "nonmouth_freeze_ratio": 0.43,
                "periodicity_peak": 0.72,
            }
        }

        report = compare_performance_features(reference, candidate)

        self.assertEqual("performance_relationship_not_pixel_similarity", report["mode"])
        self.assertEqual("reject_and_rerender", report["recommendation"])
        codes = {finding["code"] for finding in report["findings"]}
        self.assertIn("hands_move_without_whole_person", codes)
        self.assertIn("living_idle_collapse", codes)
        self.assertIn("periodic_motion_risk", codes)
        serialized = json.dumps(report, ensure_ascii=False).lower()
        self.assertNotIn("ssim", serialized)
        self.assertNotIn("psnr", serialized)

    def test_cli_writes_local_report_and_contact_sheet_for_real_media(self):
        reference = (
            SKILL_ROOT
            / "assets"
            / "performance-references"
            / "business-human-123.mp4"
        )
        candidate_path = os.environ.get("DIGITAL_HUMAN_QA_CANDIDATE")
        if not candidate_path:
            self.skipTest("DIGITAL_HUMAN_QA_CANDIDATE is not configured")
        candidate = Path(candidate_path)
        if not reference.is_file() or not candidate.is_file():
            self.skipTest("private local performance fixtures are unavailable")

        from scripts.compare_performance_reference import run_comparison

        with tempfile.TemporaryDirectory() as directory:
            report = run_comparison(
                reference=reference,
                candidate=candidate,
                output_dir=Path(directory),
                sample_fps=4.0,
                max_analysis_seconds=12.0,
            )
            self.assertEqual("business-human-123-v1", report["reference"]["id"])
            self.assertEqual(
                hashlib.sha256(candidate.read_bytes()).hexdigest(),
                report["candidate"]["sha256"],
            )
            self.assertEqual(
                "performance_relationship_not_pixel_similarity", report["comparison"]["mode"]
            )
            self.assertEqual("reject_and_rerender", report["comparison"]["recommendation"])
            self.assertIn(
                "hands_move_without_whole_person",
                {item["code"] for item in report["comparison"]["findings"]},
            )
            self.assertEqual(
                "macos_vision_median",
                report["reference"]["features"]["analysis"]["face_detection"],
            )
            self.assertTrue((Path(directory) / "performance-qc.json").is_file())
            self.assertTrue((Path(directory) / "realism-review.md").is_file())
            self.assertTrue((Path(directory) / "comparison-contact-sheet.jpg").is_file())
            self.assertNotIn("identity_similarity", report["comparison"])


if __name__ == "__main__":
    unittest.main()
