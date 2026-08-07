import json
import unittest

from scripts.dhflow.content_director import analyze_script
from scripts.dhflow.heygen_web import (
    build_web_submission_plan,
    classify_render_evidence,
)
from scripts.dhflow.performance_director import plan_performance
from scripts.dhflow.visual_director import plan_visual
from scripts.dhflow.voice_director import plan_voice


SCRIPT = "企业培训必须从真实业务开始，先解决一个高频问题，再复制成功经验。"


def _director_plans():
    beats = analyze_script(SCRIPT)
    return (
        plan_voice(beats, "professional-trustworthy-business"),
        plan_visual(
            [beat["role"] for beat in beats],
            {"aspect_ratio": "9:16", "resolution": "720p"},
            identity_alias="image1",
            hand_topology="separated",
        ),
        plan_performance(beats, "separated", "business-human-1"),
    )


class HeyGenWebPlanTests(unittest.TestCase):
    def test_plan_binds_exact_assets_script_settings_and_motion(self):
        voice_plan, visual_plan, performance_plan = _director_plans()

        plan = build_web_submission_plan(
            script=SCRIPT,
            voice_plan=voice_plan,
            visual_plan=visual_plan,
            performance_plan=performance_plan,
            voice_id="voice-1",
            avatar_group_id="group-1",
        )

        self.assertEqual("heygen-web-plan-credits", plan["transport"])
        self.assertEqual(SCRIPT, plan["preSubmit"]["exactScript"])
        self.assertEqual("voice-1", plan["preSubmit"]["requiredVoiceId"])
        self.assertEqual(
            "group-1", plan["preSubmit"]["requiredAvatarGroupId"]
        )
        self.assertEqual("9:16", plan["preSubmit"]["aspectRatio"])
        self.assertEqual("720p", plan["preSubmit"]["resolution"])
        self.assertEqual("avatar_iv", plan["preSubmit"]["engine"])
        self.assertTrue(plan["preSubmit"]["motionPrompt"])
        self.assertEqual(
            [
                "openLoggedInHeyGen",
                "selectOrUploadApprovedLook",
                "bindExactVoice",
                "enterExactScript",
                "setAvatarIvPortrait720p",
                "disableExtras",
                "applyMotionPrompt",
                "verifyBeforeSpend",
                "clickGenerate",
                "verifyRealRender",
                "pollExistingVideo",
            ],
            plan["actionOrder"],
        )
        serialized = json.dumps(plan, ensure_ascii=False)
        self.assertNotIn("mcp__codex_apps__heygen_create_speech", serialized)
        self.assertNotIn(
            "mcp__codex_apps__heygen_create_video_from_avatar", serialized
        )

    def test_rejects_rewritten_script_and_more_than_one_candidate(self):
        voice_plan, visual_plan, performance_plan = _director_plans()
        with self.assertRaisesRegex(ValueError, "exact script"):
            build_web_submission_plan(
                script=f"{SCRIPT}改写",
                voice_plan=voice_plan,
                visual_plan=visual_plan,
                performance_plan=performance_plan,
                voice_id="voice-1",
                avatar_group_id="group-1",
            )

        visual_plan["job_look"]["candidate_count"] = 2
        with self.assertRaisesRegex(ValueError, "one candidate"):
            build_web_submission_plan(
                script=SCRIPT,
                voice_plan=voice_plan,
                visual_plan=visual_plan,
                performance_plan=performance_plan,
                voice_id="voice-1",
                avatar_group_id="group-1",
            )

    def test_blueprint_is_not_rendering(self):
        self.assertEqual(
            "blueprint_ready",
            classify_render_evidence(
                session_status="thinking",
                progress=0,
                video_count=0,
                generate_button_visible=True,
                avatar_bound=False,
                resource_type="blueprint",
            ),
        )

    def test_generating_requires_bound_avatar_and_real_video(self):
        self.assertEqual(
            "rendering",
            classify_render_evidence(
                session_status="generating",
                progress=5,
                video_count=1,
                generate_button_visible=False,
                avatar_bound=True,
                resource_type="video",
            ),
        )
        self.assertEqual(
            "blocked",
            classify_render_evidence(
                session_status="generating",
                progress=5,
                video_count=1,
                generate_button_visible=False,
                avatar_bound=False,
                resource_type="video",
            ),
        )
