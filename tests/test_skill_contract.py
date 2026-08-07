from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_uses_requested_user_facing_name(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        ui = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")

        self.assertIn("# 数字人skill", skill)
        self.assertIn('display_name: "数字人skill"', ui)
        self.assertIn("数字人skill", ui)
        self.assertIn("$rachel-digital-human-production", ui)

    def test_skill_requires_per_job_image_question_and_exact_adoption(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("是否调用内置生图模型生成新的老板形象", text)
        self.assertIn("明确回复“采用”", text)
        self.assertIn("原始图片1", text)
        self.assertIn("每个任务", text)

    def test_active_contract_forbids_api_credit_creation_tools(self):
        active = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "SKILL.md",
                "references/framework.md",
                "references/checklists.md",
                "references/api-facts.md",
                "references/browser-submission.md",
            )
        )
        self.assertNotIn("mcp__codex_apps__heygen_create_speech", active)
        self.assertNotIn(
            "mcp__codex_apps__heygen_create_video_from_avatar", active
        )
        self.assertIn("网页套餐额度", active)

    def test_skill_defines_truthful_generation_evidence(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "thinking",
            "progress=0",
            "blueprint",
            "生成按钮",
            "不得报告“正在生成”",
            "稳定 video ID",
        ):
            self.assertIn(required, text)

    def test_skill_auto_binds_and_submits_without_manual_user_steps(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("自动绑定", text)
        self.assertIn("点击一次生成", text)
        self.assertIn("不得要求用户手动选择", text)
        self.assertIn("严格串行", text)

    def test_browser_reference_uses_resilient_visible_page_controls(self):
        text = (ROOT / "references/browser-submission.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "accessibility role",
            "可见标签",
            "缩略图",
            "Avatar IV",
            "9:16",
            "720P",
            "动作提示",
            "点击一次",
            "精确阻塞原因",
        ):
            self.assertIn(required, text)

    def test_ui_prompt_matches_the_new_runtime_contract(self):
        text = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$rachel-digital-human-production", text)
        self.assertIn("一张候选图", text)
        self.assertIn("采用", text)
        self.assertIn("网页套餐额度", text)
        self.assertIn("真实渲染", text)
