import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class ChatCutPostApprovalGateTests(unittest.TestCase):
    def test_skill_starts_chatcut_only_after_bound_raw_approval(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        skill_lower = skill.lower()

        self.assertIn("After the exact full raw is approved", skill)
        self.assertIn("ChatCut post-production", skill)
        self.assertIn("chatcut:chatcut-plugin-basics", skill_lower)
        self.assertIn("chatcut:verification", skill_lower)

    def test_material_choice_selects_chatcut_package(self):
        checklist = (SKILL_ROOT / "references" / "checklists.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("no-material route", checklist)
        self.assertIn("material route", checklist)
        self.assertIn("material-plan.json", checklist)
        self.assertNotIn("HyperFrames", checklist)


if __name__ == "__main__":
    unittest.main()
