from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dhflow.voice_director import plan_voice


def test_voice_plan_varies_emotion_and_intensity_by_semantic_role():
    beats = [
        {"id": "beat-001", "text": "先说结论。", "role": "hook"},
        {"id": "beat-002", "text": "为什么？", "role": "question"},
        {"id": "beat-003", "text": "先解释一下原因。", "role": "explanation"},
        {"id": "beat-004", "text": "这里有一个风险。", "role": "warning"},
        {"id": "beat-005", "text": "所以现在就行动。", "role": "conclusion"},
    ]

    plan = plan_voice(beats, persona="boss")
    deliveries = [segment["delivery"] for segment in plan["segments"]]

    assert len({delivery["emotion"] for delivery in deliveries}) > 1
    assert len({delivery["emotion_intensity"] for delivery in deliveries}) > 1
    assert all(0.0 <= delivery["emotion_intensity"] <= 1.0 for delivery in deliveries)
    intensities = [delivery["emotion_intensity"] for delivery in deliveries]
    assert max(intensities) - min(intensities) >= 0.45
    assert max(intensities) <= 0.85
    assert "emotion_arc" in plan


def test_voice_plan_preserves_approved_text_losslessly():
    beats = [
        {"id": "beat-001", "text": "开头。\n", "role": "hook"},
        {"id": "beat-002", "text": "中间，不能改字。", "role": "contrast"},
        {"id": "beat-003", "text": "最后。", "role": "conclusion"},
    ]

    plan = plan_voice(beats, persona="boss")

    assert "".join(segment["text"] for segment in plan["segments"]) == "".join(
        beat["text"] for beat in beats
    )
