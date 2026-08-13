from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_business_profile_coordinates_gaze_with_the_whole_face():
    text = (ROOT / "references" / "performance-profiles.md").read_text(
        encoding="utf-8"
    )

    assert "never move the pupils alone" in text.lower()
    assert "two-to-five-degree head adjustment" in text.lower()
    assert "slightly longer reflective blink" in text.lower()
    assert "brief downward thinking glance" in text.lower()
    assert "no forced continuous smile" in text.lower()


def test_video_submission_omits_unverified_voice_settings_by_default():
    text = (ROOT / "references" / "plugin-submission.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(text.split())

    assert "omit `voiceSettings` by default" in normalized
    assert "Do not copy parameters from `create_speech`" in normalized
    assert "materially exceeds the expected or previous baseline duration" in normalized
    assert "fail voice QA" in normalized


def test_candidate_round_requires_distinct_two_hand_pose_families():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    defaults = (ROOT / "references" / "brand-defaults.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "references" / "checklists.md").read_text(
        encoding="utf-8"
    )
    combined = " ".join((skill, defaults, checklist))

    assert "four distinct two-hand pose families" in combined
    assert "at most one candidate" in combined
    assert "gesture signature" in combined
    assert "previously adopted look" in combined
    assert "both hands resting separately" in combined
    assert "both hands lifted asymmetrically" in combined
    assert "one hand near the torso" in combined
