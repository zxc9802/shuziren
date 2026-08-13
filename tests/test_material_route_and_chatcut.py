import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class MaterialRouteAndChatCutTests(unittest.TestCase):
    def test_material_choice_is_required_before_script_approval(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        question = "这个任务是否需要加入公司素材？"
        self.assertIn(question, skill)
        self.assertLess(skill.index(question), skill.index("explicit script approval"))
        self.assertIn("On explicit no", skill)
        self.assertIn("On explicit yes", skill)
        self.assertIn("references/material-routing.md", skill)

    def test_yes_route_writes_material_grounded_copy_before_planning(self):
        routing = (
            SKILL_ROOT / "references" / "material-routing.md"
        ).read_text(encoding="utf-8")

        self.assertIn("先盘点素材，再写文案", routing)
        self.assertIn("素材相关文案", routing)
        self.assertIn("不得先写泛文案再硬塞素材", routing)
        self.assertIn("一张专属补充图片", routing)
        self.assertIn("material-plan.json", routing)

    def test_material_route_uses_only_the_most_relevant_small_set(self):
        routing = (
            SKILL_ROOT / "references" / "material-routing.md"
        ).read_text(encoding="utf-8")
        framework = (
            SKILL_ROOT / "references" / "framework.md"
        ).read_text(encoding="utf-8")

        self.assertIn("1–2 类真实公司素材", routing)
        self.assertIn("1–2 个 AI 补充素材", routing)
        self.assertIn("不得为了展示素材库而串联全部素材", routing)
        self.assertIn("1–2 类真实公司素材", framework)
        self.assertIn("1–2 个 AI 补充素材", framework)
        self.assertNotIn("one supporting generated still", framework)

    def test_post_production_uses_chatcut_not_hyperframes(self):
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        framework = (
            SKILL_ROOT / "references" / "framework.md"
        ).read_text(encoding="utf-8")
        checklist = (
            SKILL_ROOT / "references" / "checklists.md"
        ).read_text(encoding="utf-8")

        for content in (skill, framework, checklist):
            self.assertIn("ChatCut", content)
            self.assertNotIn("HyperFrames", content)
            self.assertNotIn("hyperframes:", content)


if __name__ == "__main__":
    unittest.main()
