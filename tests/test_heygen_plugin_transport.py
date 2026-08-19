import unittest

from scripts.dhflow.heygen_web import build_web_submission_plan
from scripts.dhflow.performance_director import plan_performance


class HeyGenPluginTransportTests(unittest.TestCase):
    def test_plan_uses_structured_plugin_without_overpromising_preview_duration(self):
        script = "测试脚本。"
        voice_plan = {
            "segments": [
                {
                    "id": "beat-001",
                    "text": script,
                    "delivery": {
                        "speed": "natural",
                        "emotion": "calm",
                        "emphasis": "key",
                        "pause_before": "short",
                        "pause_after": "short",
                    },
                }
            ]
        }
        visual_plan = {
            "identity_alias": "image1",
            "identity_master_alias": "image1",
            "hand_topology": "separated",
            "view_mode": "three_quarter_left_45",
            "subject_orientation": {
                "torso_yaw_degrees": 45,
                "head_yaw_degrees": 45,
                "turn_direction": "toward_frame_left",
                "gaze_anchor": "off_camera_same_direction",
            },
            "job_look": {
                "candidate_count": 1,
                "explicit_approval_required": True,
            },
            "camera": {"locked": True},
            "aspect_ratio": "9:16",
            "resolution": "720p",
        }
        performance_plan = plan_performance(
            [{"id": "beat-001", "text": script, "role": "explanation"}],
            "separated",
            view_mode="three_quarter_left_45",
        )

        plan = build_web_submission_plan(
            script=script,
            voice_plan=voice_plan,
            visual_plan=visual_plan,
            performance_plan=performance_plan,
            voice_id="voice-1",
            avatar_group_id="group-1",
        )

        self.assertEqual(plan["transport"], "heygen-plugin-structured")
        self.assertEqual(
            plan["creditSource"], "connected_heygen_subscription_credits"
        )
        self.assertNotIn("openLoggedInHeyGen", plan["actionOrder"])
        self.assertEqual(
            plan["actions"]["submitPluginVideo"]["allowedTools"],
            ["create_video_from_avatar", "create_video_from_image"],
        )
        self.assertFalse(
            plan["actions"]["submitPluginVideo"]["videoAgentAllowedForExactScript"]
        )
        self.assertEqual(plan["preSubmit"]["exactScript"], script)
        self.assertEqual(plan["preSubmit"]["requiredAvatarCapability"], "avatar_iv")
        self.assertEqual(
            plan["preSubmit"]["viewMode"],
            "three_quarter_left_45",
        )
        self.assertIn("45-degree", plan["preSubmit"]["motionPrompt"])
        self.assertIn("off-camera", plan["preSubmit"]["motionPrompt"])
        self.assertNotIn("Direct eye contact", plan["preSubmit"]["motionPrompt"])
        self.assertEqual(
            "business-human-performance-primitives-v1",
            plan["preSubmit"]["performancePrimitiveLibrary"]["id"],
        )
        self.assertEqual(
            "buildPerformanceBeatMap",
            plan["actionOrder"][4],
        )
        self.assertTrue(
            plan["preSubmit"]["guards"]["minimaxAudioPerformanceBeatMapRequired"]
        )
        self.assertTrue(plan["preSubmit"]["guards"]["viewModeMustMatchApprovedLook"])
        self.assertEqual(
            plan["preSubmit"]["previewContract"],
            {
                "targetSeconds": 15,
                "useApprovedOpeningExcerpt": True,
                "verifyActualDuration": True,
                "claimExactOnlyAfterMeasurement": True,
            },
        )
        self.assertEqual(
            plan["actions"]["resolveOrUploadApprovedLook"]["assetUploadBridge"],
            {
                "allowed": True,
                "transport": "heygen-v3-assets-only",
                "onlyForApprovedLocalArtifact": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
