import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.dhflow.planner import build_job_plan
from scripts.dhflow.state import (
    AUTO_REVIEWER,
    apply_auto_defaults,
    create_state,
    record_auto_raw_approval,
    record_image_choice,
    record_original_image_selection,
    record_preview_choice,
    record_raw_approval,
    record_raw_video,
    record_render_started,
    transition,
    validate_state,
)


ROOT = Path(__file__).resolve().parents[1]
UPDATE_SCRIPT = ROOT / "scripts" / "update_job_state.py"
PLAN_SCRIPT = ROOT / "scripts" / "plan_job.py"
RAW_SHA256 = "a" * 64
SCRIPT = "这是一段稳定可复用的企业口播文案，用来说明日常工作怎么把人工智能用起来。" * 2
REAL_EVIDENCE = {
    "session_status": "generating",
    "progress": 1,
    "video_count": 1,
    "generate_button_visible": False,
    "avatar_bound": True,
    "resource_type": "video",
}


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


def _auto_raw_qa_state(*, qa_passed=True):
    state = apply_auto_defaults(create_state(status="planned"))
    rendering = record_render_started(
        state,
        kind="full_raw",
        video_id="video-1",
        evidence=REAL_EVIDENCE,
    )
    return record_raw_video(
        rendering,
        video_id="video-1",
        content_sha256=RAW_SHA256,
        artifact_ref="outputs/full-raw.mp4",
        qa_passed=qa_passed,
    )


class AutoModeContractTests(unittest.TestCase):
    def test_skill_defines_auto_mode_without_removing_interactive_questions(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        auto = (ROOT / "references" / "auto-mode.md").read_text(encoding="utf-8")

        self.assertIn("operating_mode", skill)
        self.assertIn("全自动", skill)
        self.assertIn("Auto job order", skill)
        self.assertIn("这次配音使用 MiniMax，还是 HeyGen？", skill)
        self.assertIn("这个任务是否需要加入公司素材？", skill)
        self.assertIn("minimax", auto)
        self.assertIn("original_image1", auto)
        self.assertIn("auto-mode", auto)
        self.assertIn("Do not infer auto from silence", auto)
        self.assertIn("Never infer auto from silence", skill)


class AutoModePlannerTests(unittest.TestCase):
    def test_auto_plan_locks_minimax_original_image_and_no_preview(self):
        plan = build_job_plan(SCRIPT, _registry(), {}, operating_mode="auto")
        task = plan["task"]

        self.assertEqual("auto", task["operating_mode"])
        self.assertEqual("minimax", task["voice_provider"])
        self.assertEqual("none", task["material_route"])
        self.assertEqual("use_original", task["image_generation_choice"])
        self.assertEqual("original_image1", task["selected_image_source"])
        self.assertEqual("disabled", task["preview_choice"])
        self.assertEqual("front", task["view_mode"])
        self.assertEqual(SCRIPT, task["script"])

    def test_auto_plan_rejects_non_front_view_mode(self):
        with self.assertRaisesRegex(ValueError, "front original_image1"):
            build_job_plan(
                SCRIPT,
                _registry(),
                {"view_mode": "three_quarter_left_45"},
                operating_mode="auto",
            )


class AutoModeStateTests(unittest.TestCase):
    def test_apply_auto_defaults_skips_image_and_preview_gates(self):
        state = apply_auto_defaults(create_state(status="planned"))

        self.assertEqual("preview_choice_recorded", state["status"])
        self.assertEqual("auto", state["assets"]["job_route"]["operating_mode"])
        self.assertEqual("minimax", state["assets"]["job_route"]["voice_provider"])
        self.assertEqual("none", state["assets"]["job_route"]["material_route"])
        self.assertEqual("original_image1", state["assets"]["job_image"]["source"])
        self.assertFalse(state["assets"]["job_image"]["generate_new"])
        self.assertFalse(state["providers"]["heygen"]["preview_requested"])
        self.assertFalse(state["approval"]["image"])
        self.assertFalse(state["approval"]["preview"])
        self.assertFalse(state["approval"]["raw"])
        self.assertEqual(state, apply_auto_defaults(state))

    def test_auto_raw_approval_requires_qa_pass_and_auto_route(self):
        approved = record_auto_raw_approval(
            _auto_raw_qa_state(qa_passed=True),
            recorded_at="2026-08-16T14:00:00+08:00",
            evidence_ref="auto-mode-raw-qa-passed",
        )

        self.assertEqual("awaiting_raw_approval", approved["status"])
        self.assertTrue(approved["approval"]["raw"])
        self.assertEqual(AUTO_REVIEWER, approved["approval"]["reviewer"])
        self.assertEqual(RAW_SHA256, approved["approval"]["raw_artifact_sha256"])

        with self.assertRaisesRegex(ValueError, "must pass QA"):
            record_auto_raw_approval(
                _auto_raw_qa_state(qa_passed=False),
                recorded_at="2026-08-16T14:00:00+08:00",
                evidence_ref="auto-mode-raw-qa-passed",
            )

        interactive = record_preview_choice(
            record_original_image_selection(
                record_image_choice(create_state(status="planned"), generate_new=False)
            ),
            enabled=False,
        )
        interactive = record_render_started(
            interactive,
            kind="full_raw",
            video_id="video-1",
            evidence=REAL_EVIDENCE,
        )
        interactive = record_raw_video(
            interactive,
            video_id="video-1",
            content_sha256=RAW_SHA256,
            artifact_ref="outputs/full-raw.mp4",
            qa_passed=True,
        )
        interactive = transition(interactive, "awaiting_raw_approval")
        with self.assertRaisesRegex(ValueError, "operating_mode=auto"):
            record_raw_approval(
                interactive,
                reviewer=AUTO_REVIEWER,
                recorded_at="2026-08-16T14:00:00+08:00",
                evidence_ref="auto-mode-raw-qa-passed",
            )


class AutoModeCliTests(unittest.TestCase):
    def test_plan_job_auto_writes_locked_defaults_and_ready_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script_path = temp / "script.md"
            registry_path = temp / "registry.json"
            output_path = temp / "job"
            script_path.write_text(SCRIPT, encoding="utf-8")
            registry_path.write_text(json.dumps(_registry()), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(PLAN_SCRIPT),
                    "--script",
                    str(script_path),
                    "--registry",
                    str(registry_path),
                    "--out",
                    str(output_path),
                    "--auto",
                    "--dry-run",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            task = json.loads((output_path / "task.json").read_text(encoding="utf-8"))
            state = json.loads((output_path / "state.json").read_text(encoding="utf-8"))
            self.assertEqual("auto", task["operating_mode"])
            self.assertEqual("minimax", task["voice_provider"])
            self.assertEqual("disabled", task["preview_choice"])
            self.assertEqual("preview_choice_recorded", state["status"])
            self.assertEqual("original_image1", state["assets"]["job_image"]["source"])
            validate_state(state)

    def test_update_job_state_apply_auto_defaults_and_approve_raw_auto(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            evidence_path = Path(directory) / "render-evidence.json"
            state_path.write_text(
                json.dumps(create_state(status="planned")), encoding="utf-8"
            )
            evidence_path.write_text(json.dumps(REAL_EVIDENCE), encoding="utf-8")

            commands = (
                ("apply-auto-defaults",),
                (
                    "render-started",
                    "--kind",
                    "full_raw",
                    "--video-id",
                    "video-1",
                    "--evidence-json",
                    str(evidence_path),
                ),
                (
                    "raw-video",
                    "--video-id",
                    "video-1",
                    "--sha256",
                    RAW_SHA256,
                    "--artifact-ref",
                    "outputs/full-raw.mp4",
                    "--qa-passed",
                ),
                (
                    "approve-raw-auto",
                    "--recorded-at",
                    "2026-08-16T14:00:00+08:00",
                    "--evidence-ref",
                    "auto-mode-raw-qa-passed",
                ),
            )
            for command in commands:
                result = subprocess.run(
                    [sys.executable, str(UPDATE_SCRIPT), str(state_path), *command],
                    cwd=ROOT,
                    capture_output=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual("awaiting_raw_approval", state["status"])
            self.assertEqual(AUTO_REVIEWER, state["approval"]["reviewer"])
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
