import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from scripts.dhflow.heygen_web import build_web_submission_plan
from scripts.dhflow.performance_director import plan_performance
from scripts.verify_performance_reference import verify_reference


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "references" / "performance-reference-123.json"
REFERENCE_ID = "business-human-123-v1"
REFERENCE_SHA256 = "bba288fd4dbece4fb30f8cc5b463d3b25b1650163044a18f55c6d75bff3148ed"


def test_manifest_binds_123_as_private_performance_only_reference():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["id"] == REFERENCE_ID
    assert manifest["profile"] == "business-human-1"
    assert manifest["artifact"]["sha256"] == REFERENCE_SHA256
    assert manifest["privacy"] == {
        "private_local_only": True,
        "git_ignored": True,
        "never_upload_as_provider_input": True,
    }
    excluded = set(manifest["scope"]["exclude"])
    assert {"person identity", "voice identity", "horizontal aspect ratio"} <= excluded


def test_reference_verifier_accepts_exact_bytes_and_rejects_tampering():
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "assets" / "reference.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"private-performance-reference")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest = {
            "version": 1,
            "id": REFERENCE_ID,
            "profile": "business-human-1",
            "artifact": {
                "relative_path": "assets/reference.mp4",
                "sha256": digest,
                "size_bytes": source.stat().st_size,
            },
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        assert verify_reference(manifest_path, root=root)["sha256"] == digest
        source.write_bytes(b"tampered")
        with pytest.raises(ValueError, match="size mismatch|SHA-256 mismatch"):
            verify_reference(manifest_path, root=root)


def test_performance_plan_and_submission_are_bound_to_123_reference():
    script = "为什么企业要先解决真实问题？"
    beats = [{"id": "beat-001", "text": script, "role": "question"}]
    performance = plan_performance(beats, "separated", "business-human-1")

    assert performance["reference"]["id"] == REFERENCE_ID
    assert performance["reference"]["source_sha256"] == REFERENCE_SHA256
    assert performance["reference"]["scope"] == "performance_only"
    assert performance["motion_contract"]["whole_person_speaks"] is True
    assert performance["motion_contract"]["hands_must_not_move_alone"] is True
    beat = performance["beats"][0]
    assert beat["face"]["speech_coupled"] is True
    assert beat["head"]["neck_and_shoulders_coupled"] is True
    assert beat["body"]["living_idle"] is True

    voice_plan = {
        "segments": [
            {
                "id": "beat-001",
                "text": script,
                "delivery": {
                    "speed": "measured",
                    "emotion": "curious",
                    "emphasis": "question_core",
                    "pause_before": "short",
                    "pause_after": "medium",
                },
            }
        ]
    }
    visual_plan = {
        "identity_alias": "image1",
        "identity_master_alias": "image1",
        "hand_topology": "separated",
        "view_mode": "front",
        "subject_orientation": {
            "torso_yaw_degrees": 0,
            "head_yaw_degrees": 0,
            "turn_direction": "front",
            "gaze_anchor": "camera_lens",
        },
        "job_look": {"candidate_count": 1, "explicit_approval_required": True},
        "camera": {"locked": True},
        "aspect_ratio": "9:16",
        "resolution": "720p",
    }
    submission = build_web_submission_plan(
        script=script,
        voice_plan=voice_plan,
        visual_plan=visual_plan,
        performance_plan=performance,
        voice_id="voice-1",
        avatar_group_id="group-1",
    )

    assert submission["actionOrder"][0] == "verifyPerformanceReference"
    assert submission["preSubmit"]["performanceReference"]["id"] == REFERENCE_ID
    assert submission["preSubmit"]["guards"]["performanceReferenceMustBeVerified"]
    prompt = submission["preSubmit"]["motionPrompt"].lower()
    assert "hand stroke never moves in isolation" in prompt


def test_interactive_and_auto_contracts_both_verify_123_before_spend():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    auto = (ROOT / "references" / "auto-mode.md").read_text(encoding="utf-8")

    command = "python3 scripts/verify_performance_reference.py --json"
    assert skill.count(command) >= 2
    assert command in auto
    assert "business-human-123-v1" in auto
