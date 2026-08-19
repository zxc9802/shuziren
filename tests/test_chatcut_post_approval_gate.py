import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class ChatCutPostApprovalGateTests(unittest.TestCase):
    def test_skill_starts_chatcut_only_after_bound_raw_approval(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        skill_lower = skill.lower()

        self.assertIn("After the exact full raw is approved", skill)
        self.assertIn("ChatCut post-production", skill)
        self.assertIn("Keep executing this step here", skill)
        self.assertIn("数字人剪辑", skill)
        self.assertIn("chatcut:chatcut-plugin-basics", skill_lower)
        self.assertIn("chatcut:verification", skill_lower)

    def test_material_choice_selects_chatcut_package(self):
        checklist = (SKILL_ROOT / "references" / "checklists.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("no-material route", checklist)
        self.assertIn("material route", checklist)
        self.assertIn("material-plan.json", checklist)
        self.assertIn("mg-plan.json", checklist)
        self.assertIn("script-grounded MG", checklist)
        self.assertNotIn("HyperFrames", checklist)

    def test_chatcut_a_roll_gate_is_dual_track_and_precedes_downstream(self):
        editing = (SKILL_ROOT / "references" / "chatcut-editing.md").read_text(
            encoding="utf-8"
        )
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        auto = (SKILL_ROOT / "references" / "auto-mode.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("awaiting_a_roll_approval", editing)
        self.assertIn("a_roll_auto_qa", editing)
        self.assertIn("chatcut-a-roll-report.json", editing)
        self.assertLess(editing.index("a_roll_review"), editing.index("captions"))
        self.assertIn("references/chatcut-editing.md", skill)
        self.assertIn("reviewer `auto-mode`", auto)

    def test_chatcut_script_order_and_export_boundary_are_explicit(self):
        editing = (SKILL_ROOT / "references" / "chatcut-editing.md").read_text(
            encoding="utf-8"
        )

        script_steps = [
            "Call `read_script`",
            "run `clean_script`",
            "re-read the regenerated `timeline.md`",
            "Apply the semantic edit with `apply_script`",
        ]
        positions = [editing.index(step) for step in script_steps]
        self.assertEqual(sorted(positions), positions)
        self.assertIn("export only when the user explicitly requests", editing)
        self.assertIn("speech-led sound effects", editing)


if __name__ == "__main__":
    unittest.main()
