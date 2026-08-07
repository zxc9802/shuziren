import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.dhflow.planner import (
    DurationOutOfRangeError,
    build_job_plan,
    estimate_duration_seconds,
)
from scripts.dhflow.state import validate_state


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES_FIXTURE = ROOT / "tests" / "fixtures" / "overrides.json"


def _registry():
    return {
        "version": 2,
        "defaults": {"voice": "voice1", "identity": "image1"},
        "voices": {
            "voice1": {
                "provider": "heygen-app",
                "voice_id": "voice_abc123",
                "clone_status": "complete",
                "language": "zh",
                "speech_compatible": True,
                "source": "voice-source.mp3",
                "source_sha256": "a" * 64,
                "authorized": True,
                "persona": "professional-trustworthy-business",
            }
        },
        "identities": {
            "image1": {
                "provider": "heygen-app",
                "avatar_group_id": "group_abc123",
                "source": "portrait.png",
                "source_sha256": "b" * 64,
                "authorized": True,
                "persona": "professional-trustworthy-business",
                "performance_profile": "business-human-1",
                "hand_topology": "separated",
            }
        },
    }


class PlannerTests(unittest.TestCase):
    def test_explicit_aliases_select_authorized_future_registry_assets(self):
        registry = _registry()
        registry["voices"]["voice2"] = {
            "provider": "heygen-app",
            "voice_id": "voice_def456",
            "clone_status": "complete",
            "language": "zh",
            "speech_compatible": True,
            "source": "voice-source-2.mp3",
            "source_sha256": "c" * 64,
            "authorized": True,
            "persona": "professional-trustworthy-business",
        }
        registry["identities"]["image2"] = {
            "provider": "heygen-app",
            "avatar_group_id": "group_def456",
            "source": "portrait-2.png",
            "source_sha256": "d" * 64,
            "authorized": True,
            "persona": "professional-trustworthy-business",
            "performance_profile": "business-human-1",
            "hand_topology": "separated",
        }

        plan = build_job_plan(
            "这是一段稳定可复用的企业口播文案。" * 4,
            registry,
            {},
            voice_alias="voice2",
            identity_alias="image2",
        )

        self.assertEqual("voice2", plan["task"]["voice_alias"])
        self.assertEqual("image2", plan["task"]["identity_alias"])
        self.assertEqual(
            "professional-trustworthy-business", plan["voice_plan"]["persona"]
        )
        self.assertEqual("image2", plan["visual_plan"]["identity_alias"])
        self.assertEqual("separated", plan["visual_plan"]["hand_topology"])
        self.assertEqual("separated", plan["performance_plan"]["hand_topology"])

    def test_explicit_aliases_reject_unknown_unauthorized_and_invalid_records(self):
        script = "这是一段稳定可复用的企业口播文案。" * 4
        unauthorized_voice = _registry()
        unauthorized_voice["voices"]["voice2"] = {
            **unauthorized_voice["voices"]["voice1"],
            "voice_id": "voice_def456",
            "source": "voice-source-2.mp3",
            "source_sha256": "c" * 64,
            "authorized": False,
        }
        incomplete_identity = _registry()
        incomplete_identity["identities"]["image2"] = {
            **incomplete_identity["identities"]["image1"],
            "avatar_group_id": "group_def456",
            "source": "portrait-2.png",
            "source_sha256": "d" * 64,
        }
        del incomplete_identity["identities"]["image2"]["performance_profile"]

        cases = (
            (_registry(), {"voice_alias": "missing"}, "voices.missing"),
            (_registry(), {"identity_alias": "missing"}, "identities.missing"),
            (unauthorized_voice, {"voice_alias": "voice2"}, "authorized"),
            (
                incomplete_identity,
                {"identity_alias": "image2"},
                "performance_profile",
            ),
        )
        for registry, aliases, message in cases:
            with self.subTest(aliases=aliases):
                with self.assertRaisesRegex(ValueError, message):
                    build_job_plan(script, registry, {}, **aliases)

    def test_emits_all_director_artifacts_and_applies_overrides(self):
        script = (
            "为什么企业要做AI？很多团队一开始就买很多工具，反而没有解决真实问题。"
            "先选择一个高频场景，整理好企业知识，再设置明确的验收标准。"
            "从一个流程开始测试，让效率、质量和成本都能被衡量。"
        )

        plan = build_job_plan(
            script=script,
            registry=_registry(),
            overrides={"wardrobe": "navy_suit", "aspect_ratio": "9:16"},
        )

        self.assertEqual(
            {
                "task",
                "content_beats",
                "voice_plan",
                "visual_plan",
                "performance_plan",
                "heygen_app_plan",
            },
            set(plan),
        )
        self.assertEqual("navy_suit", plan["visual_plan"]["wardrobe"])
        self.assertEqual("9:16", plan["visual_plan"]["aspect_ratio"])
        self.assertEqual("voice1", plan["task"]["voice_alias"])
        self.assertEqual("image1", plan["task"]["identity_alias"])
        self.assertEqual("pending", plan["task"]["image_generation_choice"])
        self.assertEqual("pending", plan["task"]["selected_image_source"])
        self.assertEqual("pending", plan["task"]["preview_choice"])
        self.assertEqual("image1", plan["visual_plan"]["identity_master_alias"])
        self.assertEqual("720p", plan["task"]["raw_review_resolution"])
        self.assertEqual(script, plan["task"]["script"])
        self.assertEqual(script, "".join(beat["text"] for beat in plan["content_beats"]))
        self.assertEqual(script, "".join(
            segment["text"] for segment in plan["voice_plan"]["segments"]
        ))
        self.assertEqual(script, "".join(
            beat["text"] for beat in plan["performance_plan"]["beats"]
        ))
        self.assertEqual(
            "heygen-web-plan-credits", plan["heygen_app_plan"]["transport"]
        )
        self.assertEqual(
            "voice_abc123",
            plan["heygen_app_plan"]["preSubmit"]["requiredVoiceId"],
        )
        self.assertEqual(
            "group_abc123",
            plan["heygen_app_plan"]["preSubmit"]["requiredAvatarGroupId"],
        )
        serialized = json.dumps(plan, ensure_ascii=False)
        self.assertNotIn("minimax", serialized.lower())
        self.assertNotIn("heygen_create_speech", serialized)
        self.assertNotIn("heygen_create_video_from_avatar", serialized)

    def test_duration_boundaries_are_inclusive_and_outside_values_are_gated(self):
        for length, expected_seconds in ((60, 15.0), (360, 90.0)):
            with self.subTest(length=length):
                plan = build_job_plan("字" * length, _registry(), {})
                self.assertEqual(expected_seconds, plan["task"]["estimated_duration_seconds"])
                self.assertEqual("ready", plan["task"]["duration_status"])

        for length, reason in (
            (59, "estimated_duration_too_short"),
            (361, "estimated_duration_too_long"),
        ):
            script = "字" * length
            with self.subTest(length=length):
                with self.assertRaises(DurationOutOfRangeError) as raised:
                    build_job_plan(script, _registry(), {})

                status = raised.exception.status
                self.assertEqual("needs_script_confirmation", status["status"])
                self.assertEqual(reason, status["reason"])
                self.assertEqual(script, status["script"])
                self.assertTrue(status["rewrite_suggestion"])

    def test_duration_counts_non_bmp_cjk_and_long_numbers_as_spoken_units(self):
        non_bmp_cjk = "\U00020000" * 60
        long_number = "1" * 60

        self.assertEqual(15.0, estimate_duration_seconds(non_bmp_cjk))
        self.assertEqual(15.0, estimate_duration_seconds(long_number))
        self.assertEqual(
            "ready",
            build_job_plan(non_bmp_cjk, _registry(), {})["task"]["duration_status"],
        )
        self.assertEqual(
            "ready",
            build_job_plan(long_number, _registry(), {})["task"]["duration_status"],
        )
        with self.assertRaises(DurationOutOfRangeError):
            build_job_plan("1" * 59, _registry(), {})

    def test_registry_selects_identity_profile_and_topology(self):
        registry = _registry()
        registry["defaults"]["identity"] = "image2"
        registry["identities"]["image2"] = {
            "provider": "heygen-app",
            "avatar_group_id": "group_def456",
            "source": "alternate.png",
            "source_sha256": "d" * 64,
            "authorized": True,
            "persona": "professional-trustworthy-business",
            "performance_profile": "business-human-1",
            "hand_topology": "separated",
        }
        script = "这是一段稳定可复用的企业口播文案。" * 4

        plan = build_job_plan(
            script,
            registry,
            {"wardrobe": "linen_shirt"},
        )

        self.assertEqual("voice1", plan["task"]["voice_alias"])
        self.assertEqual("image2", plan["task"]["identity_alias"])
        self.assertEqual("image2", plan["visual_plan"]["identity_alias"])
        self.assertEqual("separated", plan["visual_plan"]["hand_topology"])
        self.assertEqual("business-human-1", plan["performance_plan"]["profile"])
        self.assertEqual("separated", plan["performance_plan"]["hand_topology"])
        self.assertEqual("linen_shirt", plan["visual_plan"]["wardrobe"])

    def test_rejects_registry_owned_and_unknown_override_fields(self):
        script = "这是一段稳定可复用的企业口播文案。" * 4
        forbidden_fields = (
            "voice_alias",
            "identity_alias",
            "source",
            "provider",
            "provider_voice_id",
            "authorized",
            "persona",
            "performance_profile",
            "hand_topology",
        )
        for field in forbidden_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    build_job_plan(script, _registry(), {field: "spoofed"})

        with self.assertRaisesRegex(ValueError, "wardobe"):
            build_job_plan(script, _registry(), {"wardobe": "navy_suit"})

        with self.assertRaisesRegex(ValueError, "pose.source"):
            build_job_plan(script, _registry(), {"pose": {"source": "spoofed"}})

    def test_rejects_registry_fields_hidden_in_override_values(self):
        script = "这是一段稳定可复用的企业口播文案。" * 4
        cases = (
            {"pose": {"posture": {"source": "portrait.png"}}},
            {"wardrobe": {"provider_voice_id": "voice-id"}},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    build_job_plan(script, _registry(), overrides)

    def test_validates_override_value_shapes_and_accepts_supported_nested_values(self):
        script = "这是一段稳定可复用的企业口播文案。" * 4
        invalid = (
            {"wardrobe": []},
            {"props": "laptop"},
            {"props": ["laptop", 1]},
            {"pose": []},
            {"pose": {"posture": 1}},
            {"camera": {"lens": False}},
            {"safe_areas": {"platform_margin": []}},
            {"image_qa_requirements": "brand_logo_clear"},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    build_job_plan(script, _registry(), overrides)

        overrides = {
            "wardrobe": "navy_suit",
            "background": "source",
            "framing": "medium_shot",
            "aspect_ratio": "9:16",
            "platform": "douyin",
            "resolution": "720p",
            "props": ["laptop", "authorized"],
            "pose": {"posture": "upright", "lead_hand_side": "left"},
            "camera": {"lens": "portrait", "angle": "profile", "height": "eye_level"},
            "safe_areas": {"platform_margin": "custom"},
            "image_qa_requirements": ["brand_logo_clear", "persona"],
        }

        plan = build_job_plan(script, _registry(), overrides)

        self.assertEqual(overrides, plan["task"]["overrides"])
        self.assertEqual("upright", plan["visual_plan"]["pose"]["posture"])
        self.assertEqual("portrait", plan["visual_plan"]["camera"]["lens"])
        self.assertIn("brand_logo_clear", plan["visual_plan"]["image_qa_requirements"])
        self.assertIn("persona", plan["visual_plan"]["image_qa_requirements"])

    def test_rejects_cyclic_override_containers_with_value_error(self):
        script = "这是一段稳定可复用的企业口播文案。" * 4
        cyclic_pose = {}
        cyclic_pose["posture"] = cyclic_pose
        cyclic_props = []
        cyclic_props.append(cyclic_props)

        for overrides in ({"pose": cyclic_pose}, {"props": cyclic_props}):
            with self.subTest(kind=next(iter(overrides))):
                with self.assertRaisesRegex(ValueError, "cyclic"):
                    build_job_plan(script, _registry(), overrides)

    def test_rejects_unauthorized_registry_assets(self):
        registry = _registry()
        registry["voices"]["voice1"]["authorized"] = False
        script = "这是一段用于规划数字人的测试文案。" * 4

        with self.assertRaisesRegex(ValueError, "authorized"):
            build_job_plan(script, registry, {})

    def test_plan_is_deterministic(self):
        script = "为什么要从一个场景开始？先测试一个流程，再根据结果持续优化。" * 3
        overrides = {"background": "technology_office"}

        self.assertEqual(
            build_job_plan(script, _registry(), overrides),
            build_job_plan(script, _registry(), overrides),
        )

    def test_cli_dry_run_writes_one_complete_planned_job(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script_path = temp / "script.md"
            registry_path = temp / "registry.json"
            output_path = temp / "job"
            script = "企业做AI不要一开始就购买很多工具。" * 4
            script_path.write_text(script, encoding="utf-8")
            registry_path.write_text(
                json.dumps(_registry(), ensure_ascii=False), encoding="utf-8"
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "plan_job.py"),
                    "--script",
                    str(script_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(output_path),
                    "--overrides",
                    str(OVERRIDES_FIXTURE),
                    "--voice-alias",
                    "voice1",
                    "--identity-alias",
                    "image1",
                    "--dry-run",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            expected_files = {
                "task.json",
                "content-beats.json",
                "voice-plan.json",
                "visual-plan.json",
                "performance-plan.json",
                "heygen-app-plan.json",
                "state.json",
            }
            self.assertEqual(expected_files, {path.name for path in output_path.iterdir()})
            task = json.loads((output_path / "task.json").read_text(encoding="utf-8"))
            visual = json.loads((output_path / "visual-plan.json").read_text(encoding="utf-8"))
            app_plan = json.loads(
                (output_path / "heygen-app-plan.json").read_text(encoding="utf-8")
            )
            state = json.loads((output_path / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(script, task["script"])
            self.assertEqual("voice1", task["voice_alias"])
            self.assertEqual("image1", task["identity_alias"])
            self.assertEqual("pending", task["preview_choice"])
            self.assertEqual("720p", task["raw_review_resolution"])
            self.assertEqual("navy_suit", visual["wardrobe"])
            self.assertEqual("9:16", visual["aspect_ratio"])
            self.assertEqual("heygen-web-plan-credits", app_plan["transport"])
            self.assertEqual(
                "voice_abc123", app_plan["preSubmit"]["requiredVoiceId"]
            )
            self.assertEqual(
                "group_abc123",
                app_plan["preSubmit"]["requiredAvatarGroupId"],
            )
            self.assertEqual("planned", state["status"])
            self.assertEqual(3, state["version"])
            self.assertEqual(
                {"image": False, "preview": False, "raw": False},
                state["approval"],
            )
            self.assertEqual({}, state["providers"])
            self.assertEqual({}, state["artifacts"])
            self.assertNotIn("migration", state)
            validate_state(state)

    def test_cli_help_exposes_trusted_asset_alias_selection(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "plan_job.py"), "--help"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("--voice-alias", completed.stdout)
        self.assertIn("--identity-alias", completed.stdout)

    def test_cli_duration_error_does_not_create_partial_job(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script_path = temp / "script.md"
            registry_path = temp / "registry.json"
            output_path = temp / "job"
            script = "短" * 10
            script_path.write_text(script, encoding="utf-8")
            registry_path.write_text(json.dumps(_registry()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "plan_job.py"),
                    "--script",
                    str(script_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(output_path),
                    "--dry-run",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertNotEqual(0, completed.returncode)
            status = json.loads(completed.stderr)
            self.assertEqual("needs_script_confirmation", status["status"])
            self.assertEqual(script, status["script"])
            self.assertFalse(output_path.exists())

    def test_cli_emits_utf8_without_python_encoding_environment(self):
        clean_env = os.environ.copy()
        clean_env.pop("PYTHONUTF8", None)
        clean_env.pop("PYTHONIOENCODING", None)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            registry_path = temp / "registry.json"
            registry_path.write_text(json.dumps(_registry()), encoding="utf-8")

            valid_script_path = temp / "valid.md"
            valid_script_path.write_text("这是一段可生成计划的中文文案。" * 5, encoding="utf-8")
            output_path = temp / "数字人任务"
            success = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "plan_job.py"),
                    "--script",
                    str(valid_script_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(output_path),
                    "--dry-run",
                ],
                cwd=ROOT,
                env=clean_env,
                capture_output=True,
            )

            self.assertEqual(0, success.returncode, success.stderr)
            self.assertIn("数字人任务", success.stdout.decode("utf-8"))

            invalid_script_path = temp / "invalid.md"
            invalid_script = "这是太短的中文文案。"
            invalid_script_path.write_text(invalid_script, encoding="utf-8")
            failure = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "plan_job.py"),
                    "--script",
                    str(invalid_script_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(temp / "invalid-job"),
                    "--dry-run",
                ],
                cwd=ROOT,
                env=clean_env,
                capture_output=True,
            )

            self.assertNotEqual(0, failure.returncode)
            status = json.loads(failure.stderr.decode("utf-8"))
            self.assertEqual("needs_script_confirmation", status["status"])
            self.assertEqual(invalid_script, status["script"])
            self.assertFalse((temp / "invalid-job").exists())

    def test_cli_accepts_bom_registry_and_overrides_and_writes_bomless_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script_path = temp / "script.md"
            registry_path = temp / "registry.json"
            overrides_path = temp / "overrides.json"
            output_path = temp / "job"
            script_path.write_text("这是一段可生成计划的中文文案。" * 5, encoding="utf-8")
            registry_path.write_text(json.dumps(_registry()), encoding="utf-8-sig")
            overrides_path.write_text(
                json.dumps({"wardrobe": "navy_suit"}), encoding="utf-8-sig"
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "plan_job.py"),
                    "--script",
                    str(script_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(output_path),
                    "--overrides",
                    str(overrides_path),
                    "--dry-run",
                ],
                cwd=ROOT,
                capture_output=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            for output_file in output_path.iterdir():
                self.assertFalse(output_file.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
