import unittest

from scripts.dhflow.content_director import find_mandarin_tts_risks
from scripts.dhflow.planner import build_job_plan
from scripts.dhflow.visual_director import plan_visual


class CloseRealLookDefaultsTests(unittest.TestCase):
    def test_generated_look_matches_original_close_composition(self):
        plan = plan_visual(["explanation"], {})

        self.assertEqual(plan["composition_reference"], "original_image1")
        self.assertEqual(plan["framing"], "reference_matched_close_seated_upper_body")
        self.assertEqual(plan["camera"]["distance"], "match_original_image1_close")
        self.assertEqual(plan["editable_appearance_fields"], ["wardrobe", "background"])
        self.assertTrue(plan["background_policy"]["real_world_photographic_required"])
        self.assertIn("person_not_too_far_from_camera", plan["image_qa_requirements"])
        self.assertIn("real_world_background_photorealism", plan["image_qa_requirements"])

    def test_generated_look_supports_left_45_degree_side_view(self):
        plan = plan_visual(
            ["explanation"],
            {"view_mode": "three_quarter_left_45"},
        )

        self.assertEqual(plan["view_mode"], "three_quarter_left_45")
        self.assertEqual(plan["subject_orientation"]["torso_yaw_degrees"], 45)
        self.assertEqual(plan["subject_orientation"]["head_yaw_degrees"], 45)
        self.assertEqual(
            plan["subject_orientation"]["turn_direction"],
            "toward_frame_left",
        )
        self.assertEqual(
            plan["subject_orientation"]["gaze_anchor"],
            "off_camera_same_direction",
        )
        self.assertIn(
            "head_torso_and_gaze_match_45_degree_anchor",
            plan["image_qa_requirements"],
        )

    def test_generated_look_rejects_unknown_view_mode(self):
        with self.assertRaisesRegex(ValueError, "unknown view_mode"):
            plan_visual(["explanation"], {"view_mode": "profile_90"})


class PlannerViewModeTests(unittest.TestCase):
    def test_planning_accepts_scripts_longer_than_ninety_seconds(self):
        registry = {
            "version": 2,
            "defaults": {"voice": "voice1", "identity": "image1"},
            "voices": {
                "voice1": {
                    "provider": "heygen-app",
                    "voice_id": "voice-1",
                    "clone_status": "complete",
                    "language": "zh",
                    "speech_compatible": True,
                    "source": "C:/private/voice.wav",
                    "source_sha256": "0" * 64,
                    "authorized": True,
                    "persona": "professional-trustworthy-business",
                }
            },
            "identities": {
                "image1": {
                    "provider": "heygen-app",
                    "avatar_group_id": "group-1",
                    "source": "C:/private/image.png",
                    "source_sha256": "1" * 64,
                    "authorized": True,
                    "persona": "professional-trustworthy-business",
                    "performance_profile": "business-human-1",
                    "hand_topology": "separated",
                }
            },
        }
        script = "企业需要把人工智能稳定用到每天的业务流程里。" * 80

        plan = build_job_plan(script, registry, {})

        self.assertGreater(plan["task"]["estimated_duration_seconds"], 90)
        self.assertEqual(plan["task"]["duration_status"], "ready")

    def test_side_view_survives_end_to_end_planning(self):
        registry = {
            "version": 2,
            "defaults": {"voice": "voice1", "identity": "image1"},
            "voices": {
                "voice1": {
                    "provider": "heygen-app",
                    "voice_id": "voice-1",
                    "clone_status": "complete",
                    "language": "zh",
                    "speech_compatible": True,
                    "source": "C:/private/voice.wav",
                    "source_sha256": "0" * 64,
                    "authorized": True,
                    "persona": "professional-trustworthy-business",
                }
            },
            "identities": {
                "image1": {
                    "provider": "heygen-app",
                    "avatar_group_id": "group-1",
                    "source": "C:/private/image.png",
                    "source_sha256": "1" * 64,
                    "authorized": True,
                    "persona": "professional-trustworthy-business",
                    "performance_profile": "business-human-1",
                    "hand_topology": "separated",
                }
            },
        }
        script = (
            "企业真正需要的不是一次演示，而是把人工智能放进每天的工作流程。"
            "我们从具体岗位开始，逐步验证，再把有效方法稳定复制到团队。"
            "这样每一步都有负责人，也能持续复盘和改进。"
        )

        plan = build_job_plan(
            script,
            registry,
            {"view_mode": "three_quarter_right_45"},
        )

        self.assertEqual(plan["task"]["view_mode"], "three_quarter_right_45")
        self.assertEqual(
            plan["visual_plan"]["subject_orientation"]["turn_direction"],
            "toward_frame_right",
        )
        self.assertEqual(
            plan["performance_plan"]["view_mode"],
            "three_quarter_right_45",
        )
        self.assertIn(
            "off-camera",
            plan["heygen_app_plan"]["preSubmit"]["motionPrompt"],
        )


class MandarinTtsPhrasingTests(unittest.TestCase):
    def test_flags_observed_unnatural_or_incorrect_breaks(self):
        script = (
            "员工不会用进日常工作。"
            "员工不知道怎样把 AI 用进每天的工作。"
            "员工不知道，怎么把它用到工作里。"
            "这，才是企业 AI 真正落地的开始。"
        )

        risks = find_mandarin_tts_risks(script)
        codes = {risk["code"] for risk in risks}

        self.assertEqual(
            codes,
            {
                "unnatural_daily_work_phrase",
                "pause_after_cognitive_verb",
                "pause_inside_this_is",
            },
        )
        self.assertEqual(
            sum(risk["code"] == "unnatural_daily_work_phrase" for risk in risks),
            2,
        )

    def test_accepts_natural_spoken_mandarin(self):
        script = (
            "员工不知道怎样把 AI 用到每天的工作里。"
            "这才是企业 AI 真正落地的开始。"
        )

        self.assertEqual(find_mandarin_tts_risks(script), [])


if __name__ == "__main__":
    unittest.main()
