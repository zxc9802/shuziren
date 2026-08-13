import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VOICE_QUESTION = "这次配音使用 MiniMax，还是 HeyGen？"
MINIMAX_VOICE_ID = "huangxu1"
RETIRED_MINIMAX_VOICE_ID = "huangxu_enterprise_20260731_v2"


class VoiceProviderRoutingTests(unittest.TestCase):
    def read(self, relative_path):
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_voice_provider_is_the_first_per_job_question(self):
        skill = self.read("SKILL.md")
        material_question = "这个任务是否需要加入公司素材？"

        self.assertIn(VOICE_QUESTION, skill)
        self.assertLess(skill.index(VOICE_QUESTION), skill.index(material_question))
        self.assertIn("record `minimax` or `heygen`", skill)
        self.assertIn("never reuse an earlier voice-provider choice", skill)

    def test_minimax_route_uses_the_approved_stable_voice(self):
        skill = self.read("SKILL.md")
        routing = self.read("references/voice-routing.md")
        defaults = self.read("references/brand-defaults.md")

        for content in (skill, routing, defaults):
            self.assertIn(MINIMAX_VOICE_ID, content)
            self.assertNotIn(RETIRED_MINIMAX_VOICE_ID, content)
        self.assertIn("MiniMax (recommended)", routing)
        self.assertIn("speech-2.8-hd", routing)

    def test_every_synthesis_requires_a_script_specific_emotion_plan(self):
        skill = self.read("SKILL.md")
        routing = self.read("references/voice-routing.md")
        checklist = self.read("references/checklists.md")

        for content in (skill, routing, checklist):
            self.assertIn("voice-plan.json", content)
            self.assertIn("emotion intensity", content)
            self.assertIn("losslessly", content)
        self.assertIn("before every preview or full-script synthesis", routing.lower())

    def test_minimax_audio_is_uploaded_exactly_and_never_resynthesized(self):
        routing = self.read("references/voice-routing.md")
        submission = self.read("references/plugin-submission.md")
        checklist = self.read("references/checklists.md")

        for content in (routing, submission, checklist):
            self.assertIn("exact MiniMax audio", content)
            self.assertIn("must not re-synthesize", content)
        self.assertIn("Never silently fall back", routing)

    def test_heygen_route_keeps_the_existing_private_voice(self):
        routing = self.read("references/voice-routing.md")
        submission = self.read("references/plugin-submission.md")

        for content in (routing, submission):
            self.assertIn("HeyGen `voice1`", content)
            self.assertIn("get_voice", content)


if __name__ == "__main__":
    unittest.main()
