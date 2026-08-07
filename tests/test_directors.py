import json
import unittest
from pathlib import Path

from scripts.dhflow.content_director import _SEMANTIC_PUNCTUATION, analyze_script
from scripts.dhflow.performance_director import plan_performance
from scripts.dhflow.visual_director import plan_visual
from scripts.dhflow.voice_director import plan_voice


FIXTURES = Path(__file__).parent / "fixtures"


class ContentDirectorTests(unittest.TestCase):
    def test_question_warning_and_actionable_final_sentence_receive_roles(self):
        script = (FIXTURES / "question-warning.md").read_text(encoding="utf-8")
        beats = analyze_script(script)

        self.assertGreaterEqual(len(script), 80)
        self.assertLessEqual(len(script), 450)
        self.assertIn("question", [beat["role"] for beat in beats])
        self.assertIn("warning", [beat["role"] for beat in beats])
        self.assertEqual("conclusion", beats[-1]["role"])

    def test_preserves_chinese_punctuation_newlines_and_spaces_exactly(self):
        script = "  你准备好了吗？\n注意：别跳过这一步。  现在就开始！"

        beats = analyze_script(script)

        self.assertEqual(script, "".join(beat["text"] for beat in beats))

    def test_rejects_whitespace_only_input(self):
        with self.assertRaisesRegex(ValueError, "text"):
            analyze_script(" \n\t ")

    def test_english_cue_words_receive_semantic_roles(self):
        beats = analyze_script(
            "Want a better opening? Warning: avoid vague claims. "
            "However, examples build trust. First, name the problem. Subscribe now."
        )

        self.assertEqual(
            ["question", "warning", "contrast", "steps", "conclusion"],
            [beat["role"] for beat in beats],
        )

    def test_english_cues_do_not_match_inside_unrelated_words(self):
        beats = analyze_script(
            "A brisk pace works. Press the button. This is a fact. That seems likely."
        )

        self.assertEqual(
            ["explanation", "explanation", "explanation", "explanation"],
            [beat["role"] for beat in beats],
        )

    def test_actionable_chinese_final_sentence_is_a_conclusion(self):
        script = (
            "AI这么火，公司怎么落地？最容易踩的坑，是一开始就买很多工具。"
            "先找到一个高频场景。"
        )

        beats = analyze_script(script)

        self.assertEqual(script, "".join(beat["text"] for beat in beats))
        self.assertIn("question", [beat["role"] for beat in beats])
        self.assertIn("warning", [beat["role"] for beat in beats])
        self.assertEqual("conclusion", beats[-1]["role"])

    def test_final_imperatives_are_conclusions(self):
        for script in ("执行这一步。", "完成表格。", "Use this method."):
            with self.subTest(script=script):
                beats = analyze_script(script)

                self.assertEqual(["conclusion"], [beat["role"] for beat in beats])

    def test_final_imperative_grammar_patterns_are_conclusions(self):
        cases = (
            "执行这一步。",
            "完成表格。",
            "使用这个方法。",
            "选择一个场景。",
            "点击下方链接。",
            "关注我们。",
            "尝试这个方案。",
            "记住这一点。",
            "请执行这一步。",
            "先找到一个高频场景。",
            "Use this method.",
            "Try this approach.",
            "Choose one scenario.",
            "Click the link.",
            "Follow these steps.",
            "Remember this point.",
            "Apply this method.",
            "Complete the table.",
            "Execute this step.",
            "Start with one scenario.",
        )
        for script in cases:
            with self.subTest(script=script):
                self.assertEqual("conclusion", analyze_script(script)[-1]["role"])

    def test_final_imperative_rules_reject_descriptive_prefixes(self):
        cases = (
            "请假安排已确认。",
            "使用率正在提升。",
            "完成度达到90%。",
            "选择题很简单。",
            "Use cases are common.",
            "The start time is noon.",
            "这个项目从昨天开始。",
        )
        for script in cases:
            with self.subTest(script=script):
                self.assertEqual("explanation", analyze_script(script)[-1]["role"])

    def test_scanner_keeps_semantic_clauses_intact(self):
        cases = {
            "真的吗？！": ["真的吗？！"],
            "版本1.2存在风险。": ["版本1.2存在风险。"],
            "他说：“真的吗？”然后继续。": ["他说：“真的吗？”", "然后继续。"],
        }
        for script, expected_texts in cases.items():
            with self.subTest(script=script):
                beats = analyze_script(script)

                self.assertEqual(expected_texts, [beat["text"] for beat in beats])
                self.assertEqual(script, "".join(beat["text"] for beat in beats))
                for beat in beats:
                    self.assertTrue(beat["text"].strip().strip(_SEMANTIC_PUNCTUATION))

    def test_ellipsis_is_semantic_punctuation_and_stays_with_preceding_beat(self):
        with self.assertRaisesRegex(ValueError, "semantic content"):
            analyze_script("……")

        script = "先说明目标……然后继续。"
        beats = analyze_script(script)

        self.assertEqual(["先说明目标……", "然后继续。"], [beat["text"] for beat in beats])
        self.assertEqual(script, "".join(beat["text"] for beat in beats))

    def test_chinese_cues_do_not_match_inside_unrelated_words(self):
        cases = {
            "这个方案的区别很明显。": "explanation",
            "这是迷你版本。": "explanation",
            "这种思想很实用。": "explanation",
            "这个项目从昨天开始。": "explanation",
        }
        for script, expected_role in cases.items():
            with self.subTest(script=script):
                beats = analyze_script(script)

                self.assertEqual([expected_role], [beat["role"] for beat in beats])

    def test_steps_fixture_is_short_script_and_includes_steps_and_cta(self):
        script = (FIXTURES / "steps-cta.md").read_text(encoding="utf-8")
        beats = analyze_script(script)

        self.assertGreaterEqual(len(script), 80)
        self.assertLessEqual(len(script), 450)
        self.assertIn("steps", [beat["role"] for beat in beats])
        self.assertEqual("conclusion", beats[-1]["role"])


class VoiceDirectorTests(unittest.TestCase):
    def test_each_role_uses_its_delivery_mapping_without_provider_fields(self):
        expected_delivery = {
            "hook": ("brisk", "short", "key"),
            "question": ("measured", "medium", "question_core"),
            "explanation": ("natural", "short", "key"),
            "warning": ("deliberate", "medium", "risk"),
            "contrast": ("measured", "short", "after_turn"),
            "steps": ("natural", "short", "ordinal"),
            "conclusion": ("measured", "medium", "action"),
        }
        allowed_speeds = {"deliberate", "measured", "natural", "brisk"}
        all_segments = []
        for index, (role, (speed, pause, emphasis)) in enumerate(expected_delivery.items(), 1):
            segment = plan_voice(
                [{"id": f"beat-{index:03d}", "text": role, "role": role}],
                persona="professional",
            )["segments"][0]

            self.assertEqual(speed, segment["delivery"]["speed"])
            self.assertEqual(pause, segment["delivery"]["pause_after"])
            self.assertEqual(emphasis, segment["delivery"]["emphasis"])
            self.assertIn("pause_before", segment["delivery"])
            self.assertEqual("calm", segment["delivery"]["emotion"])
            self.assertIn(segment["delivery"]["speed"], allowed_speeds)
            all_segments.append(segment)

        serialized = json.dumps({"segments": all_segments})
        self.assertNotIn('"timestamp"', serialized)
        self.assertNotIn('"start_time"', serialized)
        self.assertNotIn('"end_time"', serialized)
        self._assert_relative_delivery({"segments": all_segments}, allowed_speeds)

    def test_voice_plan_preserves_exact_beat_text_order_and_roles(self):
        script = "你准备好了吗？\n注意：别跳过这一步。  现在就开始！"
        beats = analyze_script(script)

        plan = plan_voice(beats, persona="professional")

        self.assertEqual("professional", plan["persona"])
        self.assertEqual(script, "".join(segment["text"] for segment in plan["segments"]))
        self.assertEqual(
            [(beat["id"], beat["role"]) for beat in beats],
            [(segment["id"], segment["role"]) for segment in plan["segments"]],
        )

    def test_semantic_roles_produce_dynamic_speeds(self):
        beats = analyze_script((FIXTURES / "question-warning.md").read_text(encoding="utf-8"))

        plan = plan_voice(beats, persona="professional")

        role_speeds = {
            segment["role"]: segment["delivery"]["speed"]
            for segment in plan["segments"]
            if segment["role"] in {"question", "warning", "conclusion"}
        }
        self.assertEqual({"question", "warning", "conclusion"}, set(role_speeds))
        self.assertGreater(len(set(role_speeds.values())), 1)

    def test_adjacent_speeds_are_normalized(self):
        beats = [
            {"id": "beat-001", "text": "看这里。", "role": "hook"},
            {"id": "beat-002", "text": "这很重要。", "role": "warning"},
        ]

        plan = plan_voice(beats, persona="professional")

        levels = {"deliberate": 0, "measured": 1, "natural": 2, "brisk": 3}
        speeds = [levels[segment["delivery"]["speed"]] for segment in plan["segments"]]
        self.assertLessEqual(abs(speeds[1] - speeds[0]), 1)

    def test_rejects_malformed_or_unknown_role_beats(self):
        cases = (
            ([{"id": "beat-001", "text": "text", "role": "unknown"}], "role"),
            ([{"id": "beat-001", "role": "hook"}], "text"),
            ([{"text": "text", "role": "hook"}], "id"),
        )
        for beats, field in cases:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    plan_voice(beats, persona="professional")

    def test_rejects_empty_beat_list_and_whitespace_beat_text(self):
        with self.assertRaisesRegex(ValueError, "beats"):
            plan_voice([], persona="professional")
        with self.assertRaisesRegex(ValueError, "text"):
            plan_voice(
                [{"id": "beat-001", "text": " \n\t", "role": "hook"}],
                persona="professional",
            )

    def _assert_relative_delivery(self, value, allowed_speeds):
        if isinstance(value, dict):
            for key, nested_value in value.items():
                self.assertNotIn(key, {"timestamp", "start_time", "end_time"})
                if key == "speed":
                    self.assertIsInstance(nested_value, str)
                    self.assertIn(nested_value, allowed_speeds)
                self._assert_relative_delivery(nested_value, allowed_speeds)
        elif isinstance(value, list):
            for nested_value in value:
                self._assert_relative_delivery(nested_value, allowed_speeds)


class VisualDirectorTests(unittest.TestCase):
    def test_visual_plan_keeps_image1_as_master_and_plans_one_approved_job_look(self):
        plan = plan_visual(
            ["hook", "explanation"],
            {},
            identity_alias="image1",
            hand_topology="separated",
        )

        self.assertEqual("image1", plan["identity_master_alias"])
        self.assertEqual("pending", plan["job_look"]["generation_choice"])
        self.assertEqual(1, plan["job_look"]["candidate_count"])
        self.assertTrue(plan["job_look"]["explicit_approval_required"])
        self.assertEqual("original_image1", plan["job_look"]["fallback"])
        self.assertEqual("same_identity_group", plan["job_look"]["retention"])

    def test_visual_overrides_cannot_replace_identity_master_or_approval_gate(self):
        plan = plan_visual(
            ["warning"],
            {
                "identity_master_alias": "other",
                "job_look": {"explicit_approval_required": False},
            },
            identity_alias="image1",
            hand_topology="separated",
        )

        self.assertEqual("image1", plan["identity_master_alias"])
        self.assertTrue(plan["job_look"]["explicit_approval_required"])

    def test_visual_plan_requests_animation_ready_pose(self):
        plan = plan_visual(role_summary=["question", "warning"], overrides={})

        self.assertEqual("image1", plan["identity_alias"])
        self.assertTrue(plan["identity_invariants"])
        self.assertTrue(plan["pose"]["neutral_ready"])
        self.assertTrue(plan["pose"]["anchor_hand"])
        self.assertTrue(plan["pose"]["lead_hand_visible"])
        self.assertEqual("unobstructed", plan["mouth_visibility"])
        self.assertTrue(plan["safe_areas"])
        self.assertTrue(plan["camera"]["locked"])
        self.assertTrue(plan["image_qa_requirements"])

    def test_visual_overrides_win_after_inference_but_cannot_change_identity(self):
        plan = plan_visual(
            role_summary=["question"],
            overrides={
                "wardrobe": "denim_jacket",
                "background": "creative_studio",
                "framing": "waist_up",
                "identity_alias": "other-person",
                "identity_invariants": {"face_shape": "different"},
            },
        )

        self.assertEqual("denim_jacket", plan["wardrobe"])
        self.assertEqual("creative_studio", plan["background"])
        self.assertEqual("waist_up", plan["framing"])
        self.assertEqual("image1", plan["identity_alias"])
        self.assertNotEqual({"face_shape": "different"}, plan["identity_invariants"])

    def test_visual_plan_accepts_trusted_identity_selection_only(self):
        plan = plan_visual(
            role_summary=["explanation"],
            overrides={"identity_alias": "spoofed-image"},
            identity_alias="image2",
        )

        self.assertEqual("image2", plan["identity_alias"])
        self.assertTrue(plan["identity_invariants"])

        with self.assertRaisesRegex(ValueError, "identity_alias"):
            plan_visual(["explanation"], {}, identity_alias=" ")

    def test_visual_overrides_cannot_disable_animation_and_qa_invariants(self):
        plan = plan_visual(
            role_summary=["warning"],
            overrides={
                "pose": {
                    "neutral_ready": False,
                    "anchor_hand": False,
                    "lead_hand_visible": False,
                    "hands_separated": False,
                    "lead_hand_side": "left",
                },
                "mouth_visibility": "covered",
                "camera": {"locked": False, "lens": "portrait"},
                "safe_areas": {
                    "head_motion_space": "blocked",
                    "subtitle_zone": "blocked",
                    "platform_margin": "custom",
                },
                "image_qa_requirements": ["brand_logo_clear"],
            },
        )

        self.assertEqual(
            {
                "neutral_ready": True,
                "anchor_hand": True,
                "lead_hand_visible": True,
                "hands_separated": True,
            },
            {key: plan["pose"][key] for key in (
                "neutral_ready",
                "anchor_hand",
                "lead_hand_visible",
                "hands_separated",
            )},
        )
        self.assertEqual("left", plan["pose"]["lead_hand_side"])
        self.assertEqual("unobstructed", plan["mouth_visibility"])
        self.assertTrue(plan["camera"]["locked"])
        self.assertEqual("portrait", plan["camera"]["lens"])
        self.assertEqual("clear", plan["safe_areas"]["head_motion_space"])
        self.assertEqual("clear", plan["safe_areas"]["subtitle_zone"])
        self.assertEqual("custom", plan["safe_areas"]["platform_margin"])
        self.assertIn("identity_consistency", plan["image_qa_requirements"])
        self.assertIn("safe_area_clearance", plan["image_qa_requirements"])
        self.assertIn("brand_logo_clear", plan["image_qa_requirements"])

    def test_visual_plan_is_deterministic_and_rejects_unknown_inputs(self):
        args = {"role_summary": ["steps", "conclusion"], "overrides": {"framing": "medium_shot"}}
        self.assertEqual(plan_visual(**args), plan_visual(**args))

        with self.assertRaisesRegex(ValueError, "role"):
            plan_visual(role_summary=["unknown"], overrides={})
        with self.assertRaisesRegex(ValueError, "overrides"):
            plan_visual(role_summary=["question"], overrides=[])

    def test_not_visible_topology_is_consistent_for_close_up_source(self):
        plan = plan_visual(
            role_summary=["explanation"],
            overrides={
                "framing": "close_up",
                "pose": {
                    "anchor_hand": True,
                    "lead_hand_visible": True,
                    "hands_separated": True,
                    "posture": "upright",
                },
                "safe_areas": {"lead_hand_motion_space": "clear"},
                "image_qa_requirements": ["five_finger_structure", "brand_logo_clear"],
            },
            hand_topology="not_visible",
        )

        self.assertEqual("close_up", plan["framing"])
        self.assertEqual("not_visible", plan["hand_topology"])
        self.assertFalse(plan["pose"]["anchor_hand"])
        self.assertFalse(plan["pose"]["lead_hand_visible"])
        self.assertFalse(plan["pose"]["hands_separated"])
        self.assertTrue(plan["pose"]["synthetic_arms_prohibited"])
        self.assertEqual("upright", plan["pose"]["posture"])
        self.assertNotIn("lead_hand_motion_space", plan["safe_areas"])
        self.assertNotIn("five_finger_structure", plan["image_qa_requirements"])
        self.assertIn("no_synthetic_arms", plan["image_qa_requirements"])
        self.assertIn("brand_logo_clear", plan["image_qa_requirements"])

    def test_visual_plan_rejects_unhashable_public_inputs_with_value_error(self):
        cases = (
            {"role_summary": [[]], "overrides": {}},
            {"role_summary": ["question"], "overrides": {}, "hand_topology": []},
            {"role_summary": ["question"], "overrides": {}, "identity_alias": []},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    plan_visual(**kwargs)


class PerformanceDirectorTests(unittest.TestCase):
    def test_overlapping_hands_degrade_to_face_and_head_motion(self):
        beats = [{"id": "b1", "text": "Mind this risk.", "role": "warning", "importance": 2}]

        beat = plan_performance(
            beats,
            hand_topology="overlapping",
            profile="business-human-1",
        )["beats"][0]

        self.assertEqual("minimal", beat["hands"]["intensity"])
        self.assertTrue(beat["face"]["enabled"])
        self.assertTrue(beat["head"]["enabled"])
        self.assertTrue(beat["body"]["enabled"])

    def test_semantic_roles_map_to_business_human_actions(self):
        beats = [
            {"id": "b1", "text": "A question?", "role": "question"},
            {"id": "b2", "text": "Here is why.", "role": "explanation"},
            {"id": "b3", "text": "Avoid this risk.", "role": "warning"},
            {"id": "b4", "text": "First, do this.", "role": "steps"},
            {"id": "b5", "text": "But compare these.", "role": "contrast"},
            {"id": "b6", "text": "Use this method.", "role": "conclusion"},
        ]

        planned = plan_performance(beats, hand_topology="separated")["beats"]

        self.assertEqual("eyebrow_lift", planned[0]["face"]["action"])
        self.assertEqual("small_head_tilt", planned[0]["head"]["action"])
        self.assertIn(planned[1]["hands"]["main_action"], {"palm_up", "small_arc"})
        self.assertEqual("brow_narrow", planned[2]["face"]["action"])
        self.assertEqual("small_counting_beat", planned[3]["hands"]["main_action"])
        self.assertEqual("small_lateral_separation", planned[4]["hands"]["main_action"])
        self.assertEqual("single_nod", planned[5]["head"]["action"])

    def test_hand_actions_have_full_cycle_and_adjacent_actions_differ(self):
        beats = [
            {"id": "b1", "text": "Explain one.", "role": "explanation"},
            {"id": "b2", "text": "Explain two.", "role": "explanation"},
            {"id": "b3", "text": "Explain three.", "role": "explanation"},
        ]

        planned = plan_performance(beats, hand_topology="separated")["beats"]
        actions = [beat["hands"]["main_action"] for beat in planned]

        self.assertNotEqual(actions[0], actions[1])
        self.assertNotEqual(actions[1], actions[2])
        for beat in planned:
            self.assertEqual(
                {"prepare", "stroke", "optional_hold", "retract", "cooldown"},
                set(beat["hands"]["cycle"]),
            )

    def test_performance_plan_is_deterministic_provider_neutral_and_validated(self):
        beats = [{"id": "b1", "text": "Why?", "role": "question"}]
        first = plan_performance(beats, hand_topology="one_visible")
        second = plan_performance(beats, hand_topology="one_visible")

        self.assertEqual(first, second)
        serialized = json.dumps(first)
        for forbidden in ("timestamp", "start_time", "end_time", "seconds", "heygen"):
            self.assertNotIn(forbidden, serialized.lower())

        with self.assertRaisesRegex(ValueError, "profile"):
            plan_performance(beats, hand_topology="one_visible", profile="unknown")
        with self.assertRaisesRegex(ValueError, "hand_topology"):
            plan_performance(beats, hand_topology="unknown")
        with self.assertRaisesRegex(ValueError, "role"):
            plan_performance([{"id": "b1", "text": "x", "role": "unknown"}], "separated")

    def test_performance_plan_rejects_unhashable_inputs_with_value_error(self):
        beat = {"id": "b1", "text": "x", "role": "question"}
        with self.assertRaisesRegex(ValueError, "hand_topology"):
            plan_performance([beat], [])
        with self.assertRaisesRegex(ValueError, "role"):
            plan_performance([{"id": "b1", "text": "x", "role": []}], "separated")


if __name__ == "__main__":
    unittest.main()
