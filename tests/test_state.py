import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.dhflow.state import (
    STATES,
    create_state,
    migrate_v1,
    migrate_v2,
    record_image_approval,
    record_image_candidate,
    record_image_choice,
    record_original_image_selection,
    record_preview_approval,
    record_preview_choice,
    record_preview_result,
    record_raw_approval,
    record_raw_video,
    record_render_started,
    start_image_generation,
    transition,
    validate_state,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATE_SCRIPT = ROOT / "scripts" / "migrate_job_state.py"
UPDATE_SCRIPT = ROOT / "scripts" / "update_job_state.py"
INIT_SCRIPT = ROOT / "scripts" / "init_job_state.py"
RAW_SHA256 = "a" * 64


def _approved_raw_state():
    return {
        "version": 3,
        "status": "awaiting_raw_approval",
        "approval": {
            "image": False,
            "preview": False,
            "raw": True,
            "reviewer": "user-owner",
            "raw_artifact_sha256": RAW_SHA256,
            "heygen_video_id": "video-1",
            "recorded_at": "2026-08-06T12:00:00+08:00",
            "evidence_ref": "conversation-message-42",
        },
        "providers": {"heygen": {"video_id": "video-1"}},
        "assets": {},
        "artifacts": {
            "raw_video": {
                "kind": "full_raw",
                "sha256": RAW_SHA256,
                "qa_passed": True,
                "ref": "outputs/heygen-full-raw.mp4",
            }
        },
        "error": {},
        "retry": {},
    }


class StateTransitionTests(unittest.TestCase):
    def test_create_state_returns_valid_fresh_v3_state_without_external_work(self):
        state = create_state(status="planned")

        self.assertEqual(
            {
                "version": 3,
                "status": "planned",
                "approval": {"image": False, "preview": False, "raw": False},
                "providers": {},
                "assets": {},
                "artifacts": {},
                "error": {},
                "retry": {},
            },
            state,
        )
        validate_state(state)

    def test_states_define_the_required_order(self):
        self.assertEqual(
            (
                "created",
                "planned",
                "image_generation_choice_recorded",
                "awaiting_image_approval",
                "image_approved",
                "preview_choice_recorded",
                "preview_rendering",
                "awaiting_preview_approval",
                "full_raw_rendering",
                "raw_qa",
                "awaiting_raw_approval",
                "post_production",
                "final_qa",
                "complete",
            ),
            STATES,
        )

    def test_transition_advances_only_to_the_next_state(self):
        state = {"status": "created", "approval": {"raw": False}}

        advanced = transition(state, "planned")

        self.assertEqual("planned", advanced["status"])

    def test_transition_is_non_mutating_and_preserves_resume_metadata(self):
        state = {
            "status": "planned",
            "approval": {"raw": False},
            "providers": {"heygen": {"audio_id": "audio-1"}},
            "artifacts": {
                "audio": {
                    "sha256": "b" * 64,
                    "duration_seconds": 21.5,
                }
            },
            "error": {"stage": "audio", "message": "temporary"},
            "retry": {"audio": 1},
        }
        original = copy.deepcopy(state)

        advanced = transition(state, "image_generation_choice_recorded")

        self.assertEqual(original, state)
        self.assertEqual(original["providers"], advanced["providers"])
        self.assertEqual(original["artifacts"], advanced["artifacts"])
        self.assertEqual(original["error"], advanced["error"])
        self.assertEqual(original["retry"], advanced["retry"])
        self.assertIsNot(state["providers"], advanced["providers"])

    def test_same_state_transition_is_an_idempotent_non_mutating_copy(self):
        state = {
            "status": "raw_qa",
            "approval": {"raw": False},
            "providers": {"heygen": {"video_id": "video-1"}},
        }

        resumed = transition(state, "raw_qa")
        resumed["providers"]["heygen"]["video_id"] = "changed"

        self.assertEqual("video-1", state["providers"]["heygen"]["video_id"])
        self.assertIsNot(state, resumed)

    def test_rejects_skipped_backward_and_unknown_targets(self):
        cases = (
            ({"status": "created"}, "image_approved", "skip"),
            ({"status": "image_approved"}, "planned", "backward"),
            ({"status": "created"}, "not-a-state", "unknown"),
        )
        for state, target, message in cases:
            with self.subTest(state=state["status"], target=target):
                with self.assertRaisesRegex(ValueError, message):
                    transition(state, target)

    def test_rejects_unknown_or_malformed_current_state(self):
        for state in ({"status": "mystery"}, {"status": 3}, [], None):
            with self.subTest(state=state):
                with self.assertRaises(ValueError):
                    transition(state, "planned")

    def test_unknown_target_value_is_not_copied_to_error_text(self):
        sensitive_target = "SENSITIVE_TARGET_VALUE"

        with self.assertRaises(ValueError) as caught:
            transition({"status": "created"}, sensitive_target)

        self.assertNotIn(sensitive_target, str(caught.exception))

    def test_rejects_postproduction_before_strict_raw_approval(self):
        for raw_approval in (False, "true", "false", 1, 0, None):
            with self.subTest(raw_approval=raw_approval):
                state = {
                    "status": "awaiting_raw_approval",
                    "approval": {"raw": raw_approval},
                }
                with self.assertRaisesRegex(ValueError, "raw approval"):
                    transition(state, "post_production")

    def test_raw_approval_gate_precedes_skipped_transition_error(self):
        state = {"status": "raw_qa", "approval": {"raw": False}}

        with self.assertRaisesRegex(ValueError, "raw approval"):
            transition(state, "post_production")

    def test_bare_boolean_true_never_allows_postproduction(self):
        state = {
            "status": "awaiting_raw_approval",
            "approval": {"raw": True},
        }

        with self.assertRaisesRegex(ValueError, "raw approval evidence"):
            transition(state, "post_production")

    def test_postproduction_rejects_unbound_or_invalid_raw_artifact_evidence(self):
        cases = []

        missing_artifact = _approved_raw_state()
        missing_artifact["artifacts"] = {}
        cases.append(("missing artifact", missing_artifact))

        preview_artifact = _approved_raw_state()
        preview_artifact["artifacts"]["raw_video"]["kind"] = "preview"
        cases.append(("preview artifact", preview_artifact))

        for value in (False, "true", 1):
            invalid_qa = _approved_raw_state()
            invalid_qa["artifacts"]["raw_video"]["qa_passed"] = value
            cases.append((f"invalid qa {value!r}", invalid_qa))

        for value in ("A" * 64, "a" * 63, "not-a-hash", True, 1):
            malformed_hash = _approved_raw_state()
            malformed_hash["artifacts"]["raw_video"]["sha256"] = value
            cases.append((f"malformed artifact hash {value!r}", malformed_hash))

        mismatched_hash = _approved_raw_state()
        mismatched_hash["approval"]["raw_artifact_sha256"] = "b" * 64
        cases.append(("mismatched approval hash", mismatched_hash))

        for value in (None, "A" * 64, "a" * 63, True, 1):
            malformed_approval_hash = _approved_raw_state()
            if value is None:
                del malformed_approval_hash["approval"]["raw_artifact_sha256"]
            else:
                malformed_approval_hash["approval"]["raw_artifact_sha256"] = value
            cases.append((f"malformed approval hash {value!r}", malformed_approval_hash))

        for value in (None, "", "   ", True, 1):
            invalid_ref = _approved_raw_state()
            if value is None:
                del invalid_ref["artifacts"]["raw_video"]["ref"]
            else:
                invalid_ref["artifacts"]["raw_video"]["ref"] = value
            cases.append((f"invalid raw artifact ref {value!r}", invalid_ref))

        for field in ("reviewer", "recorded_at", "evidence_ref"):
            for value in (None, "", "   ", True, 1):
                missing_evidence = _approved_raw_state()
                if value is None:
                    del missing_evidence["approval"][field]
                else:
                    missing_evidence["approval"][field] = value
                cases.append((f"invalid {field} {value!r}", missing_evidence))

        for label, state in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ValueError,
                    r"raw (artifact|approval) (evidence|reference|timestamp)|must pass QA",
                ):
                    transition(state, "post_production")

    def test_validate_state_allows_failed_qa_artifact_during_raw_qa(self):
        state = _approved_raw_state()
        state["status"] = "raw_qa"
        state["approval"] = {"raw": False}
        state["artifacts"]["raw_video"]["qa_passed"] = False

        validate_state(state)

    def test_postproduction_rejects_failed_qa_artifact(self):
        state = _approved_raw_state()
        state["artifacts"]["raw_video"]["qa_passed"] = False

        with self.assertRaisesRegex(ValueError, "must pass QA"):
            transition(state, "post_production")

    def test_postproduction_requires_stable_full_raw_provider_video_id(self):
        for providers in ({}, {"heygen": {}}, {"heygen": {"video_id": True}}):
            state = _approved_raw_state()
            state["providers"] = providers

            with self.subTest(providers=providers):
                with self.assertRaisesRegex(ValueError, "raw artifact evidence|provider ID"):
                    transition(state, "post_production")

    def test_postproduction_requires_approval_bound_to_heygen_video_id(self):
        cases = []

        missing_approval_id = _approved_raw_state()
        del missing_approval_id["approval"]["heygen_video_id"]
        cases.append(("missing approval ID", missing_approval_id))

        mismatched_approval_id = _approved_raw_state()
        mismatched_approval_id["approval"]["heygen_video_id"] = "video-2"
        cases.append(("mismatched approval ID", mismatched_approval_id))

        invalid_approval_id = _approved_raw_state()
        invalid_approval_id["approval"]["heygen_video_id"] = True
        cases.append(("invalid approval ID", invalid_approval_id))

        for label, state in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "raw approval evidence"):
                    transition(state, "post_production")

    def test_raw_approval_rejects_timestamp_without_valid_timezone(self):
        for recorded_at in (
            "not-a-timestamp",
            "2026-02-30T12:00:00+08:00",
            "2026-08-06T12:00:00",
            "2026-08-06T12:00:00+24:00",
            "2026-08-06T12:00:00+08:60",
            "2026-08-06T12:00:00+00:99",
            "2026-08-06T12:00:00-00:00",
        ):
            state = _approved_raw_state()
            state["approval"]["recorded_at"] = recorded_at

            with self.subTest(recorded_at=recorded_at):
                with self.assertRaisesRegex(ValueError, "timestamp"):
                    transition(state, "post_production")

    def test_raw_approval_accepts_iso_timestamp_with_timezone(self):
        for recorded_at in (
            "2026-08-06T12:00:00+23:59",
            "2026-08-06T12:00:00+08:00",
            "2026-08-06T12:00:00+00:00",
            "2026-08-06T04:00:00Z",
        ):
            state = _approved_raw_state()
            state["approval"]["recorded_at"] = recorded_at

            with self.subTest(recorded_at=recorded_at):
                advanced = transition(state, "post_production")

            self.assertEqual(recorded_at, advanced["approval"]["recorded_at"])

    def test_raw_approval_rejects_unstable_or_sensitive_references(self):
        fake_jwt = (
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0."
            "dGVzdC1zaWduYXR1cmU"
        )
        fake_secret = "sk-testonly-examplevalue-1234567890"
        cases = (
            ("artifacts", "https://example.com/raw.mp4?X-Amz-Signature=secret"),
            ("artifacts", "outputs/raw.mp4?token=secret"),
            ("artifacts", "outputs/raw.mp4#access_token=secret"),
            ("artifacts", "Authorization: Bearer secret"),
            ("artifacts", "s3://private-bucket/raw.mp4"),
            ("approval", "Bearer secret"),
            ("approval", "Basic dXNlcjpwYXNz"),
            ("approval", "token=secret"),
            (
                "approval",
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature",
            ),
            ("approval", "sk-secretvalue"),
            ("approval", f"jwt={fake_jwt}"),
            ("approval", f"({fake_jwt})"),
            ("approval", f"[{fake_secret}]"),
            ("approval", f"{fake_secret},"),
            ("approval", "note,Bearer fake-bearer-value"),
            ("approval", "auth/Basic ZmFrZTpjcmVkZW50aWFs"),
            ("approval", "note-Bearer fake-credential-value"),
            ("approval", "auth_Basic ZmFrZTpjcmVkZW50aWFs"),
            ("approval", "Bearer secret.txt"),
            ("approval", "audit/Bearer secret.txt"),
            (
                "approval",
                "auth/Basic ZmFrZTpjcmVkZW50aWFs/file.mp4",
            ),
            ("approval", "note-Bearer secret.mp4"),
            ("approval", "outputs/evidence.txt"),
            ("approval", r"C:\evidence\approval.txt"),
            ("approval", "conversation/message-42"),
            ("approval", "./approval-event-42"),
            ("approval", f"ref-{fake_secret}"),
            ("approval", f"ref-{fake_jwt}"),
            ("approval", f"jwt_{fake_jwt}"),
            ("approval", "audit-42\nAuthorization: Bearer secret"),
        )
        for location, reference in cases:
            state = _approved_raw_state()
            if location == "artifacts":
                state["artifacts"]["raw_video"]["ref"] = reference
            else:
                state["approval"]["evidence_ref"] = reference

            with self.subTest(location=location, reference=reference):
                with self.assertRaisesRegex(ValueError, "reference"):
                    transition(state, "post_production")

    def test_raw_approval_accepts_stable_local_and_opaque_references(self):
        state = _approved_raw_state()
        state["artifacts"]["raw_video"]["ref"] = "outputs/full-raw.mp4"
        state["approval"]["evidence_ref"] = "conversation-message-42"

        advanced = transition(state, "post_production")

        self.assertEqual(
            "outputs/full-raw.mp4", advanced["artifacts"]["raw_video"]["ref"]
        )
        self.assertEqual(
            "conversation-message-42", advanced["approval"]["evidence_ref"]
        )

    def test_raw_approval_accepts_windows_absolute_and_hyphenated_opaque_refs(self):
        state = _approved_raw_state()
        state["artifacts"]["raw_video"]["ref"] = r"C:\outputs\full-raw.mp4"
        state["approval"]["evidence_ref"] = "approval-event-alpha-42"

        advanced = transition(state, "post_production")

        self.assertEqual(
            r"C:\outputs\full-raw.mp4", advanced["artifacts"]["raw_video"]["ref"]
        )
        self.assertEqual(
            "approval-event-alpha-42", advanced["approval"]["evidence_ref"]
        )

    def test_raw_approval_accepts_benign_credential_words_without_values(self):
        for evidence_ref in ("bearer-ticket-42", "sketch-reference-42"):
            state = _approved_raw_state()
            state["approval"]["evidence_ref"] = evidence_ref

            with self.subTest(evidence_ref=evidence_ref):
                advanced = transition(state, "post_production")

            self.assertEqual(evidence_ref, advanced["approval"]["evidence_ref"])

    def test_raw_approval_accepts_benign_sk_word_and_basic_file_paths(self):
        cases = (
            ("approval", "task-api-key-rotation"),
            ("artifact", "outputs/basic footage.mp4"),
            ("artifact", r"C:\Basic Projects\full-raw.mp4"),
        )
        for location, reference in cases:
            state = _approved_raw_state()
            if location == "approval":
                state["approval"]["evidence_ref"] = reference
            else:
                state["artifacts"]["raw_video"]["ref"] = reference

            with self.subTest(location=location, reference=reference):
                advanced = transition(state, "post_production")
                if location == "approval":
                    self.assertEqual(reference, advanced["approval"]["evidence_ref"])
                else:
                    self.assertEqual(
                        reference, advanced["artifacts"]["raw_video"]["ref"]
                    )

    def test_raw_approval_rejects_one_letter_hierarchical_uri(self):
        state = _approved_raw_state()
        state["artifacts"]["raw_video"]["ref"] = "x://remote.example/raw.mp4"

        with self.assertRaisesRegex(ValueError, "reference"):
            transition(state, "post_production")

    def test_allows_postproduction_only_with_bound_full_raw_approval_evidence(self):
        state = _approved_raw_state()
        original = copy.deepcopy(state)

        advanced = transition(state, "post_production")

        self.assertEqual(original, state)
        self.assertEqual("post_production", advanced["status"])
        self.assertEqual("video-1", advanced["providers"]["heygen"]["video_id"])
        self.assertEqual("video-1", advanced["approval"]["heygen_video_id"])
        self.assertEqual(RAW_SHA256, advanced["approval"]["raw_artifact_sha256"])
        resumed = transition(advanced, "post_production")
        self.assertEqual(advanced, resumed)
        self.assertIsNot(advanced, resumed)

    def test_validate_state_rejects_malformed_approval_and_non_json_metadata(self):
        cases = (
            ({"status": "created", "approval": []}, "approval"),
            ({"status": "created", "approval": {"raw": "true"}}, "raw approval"),
            ({"status": "created", "retry": {"stage": object()}}, "JSON"),
        )
        for state, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    validate_state(state)

    def test_transition_rejects_nested_nonfinite_metadata(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                state = {
                    "status": "created",
                    "retry": {"delay_seconds": value},
                }

                with self.assertRaisesRegex(ValueError, "standard JSON"):
                    transition(state, "planned")

    def test_transition_allows_only_schema_defined_heygen_provider_ids(self):
        state = {
            "status": "created",
            "providers": {
                "heygen": {
                    "preview_video_id": "video-token-1",
                    "audio_id": "audio-1",
                }
            },
        }

        advanced = transition(state, "planned")

        self.assertEqual(state["providers"], advanced["providers"])
        with self.assertRaisesRegex(ValueError, "unsupported provider field"):
            transition(
                {
                    "status": "created",
                    "providers": {"heygen": {"provider_access_id": "provider-1"}},
                },
                "planned",
            )

    def test_transition_rejects_nonstandard_programmatic_json_types(self):
        class DictSubclass(dict):
            pass

        class ListSubclass(list):
            pass

        class IntSubclass(int):
            pass

        invalid_metadata = (
            {1: "integer key"},
            {True: "boolean key"},
            ("tuple",),
            {"set"},
            DictSubclass({"value": 1}),
            ListSubclass([1]),
            IntSubclass(1),
            object(),
        )
        for metadata in invalid_metadata:
            with self.subTest(type=type(metadata).__name__):
                with self.assertRaisesRegex(ValueError, "standard JSON"):
                    transition(
                        {"status": "created", "metadata": metadata},
                        "planned",
                    )


class ImageApprovalStateTests(unittest.TestCase):
    def test_no_new_image_selects_original_image1(self):
        state = create_state(status="planned")

        choice = record_image_choice(state, generate_new=False)
        chosen = record_original_image_selection(choice)

        self.assertEqual("image_generation_choice_recorded", choice["status"])
        self.assertEqual("image_approved", chosen["status"])
        self.assertEqual(
            "original_image1", chosen["assets"]["job_image"]["source"]
        )
        self.assertEqual(
            "image1", chosen["assets"]["job_image"]["identity_master_alias"]
        )

    def test_new_image_requires_candidate_and_bound_approval(self):
        choice = record_image_choice(
            create_state(status="planned"), generate_new=True
        )
        state = start_image_generation(choice)

        self.assertEqual("awaiting_image_approval", state["status"])
        with self.assertRaisesRegex(ValueError, "candidate image"):
            record_image_approval(
                state,
                reviewer="user",
                recorded_at="2026-08-07T12:00:00+08:00",
                evidence_ref="conversation-message-image-1",
            )

    def test_image_approval_binds_exact_candidate_without_other_approvals(self):
        choice = record_image_choice(
            create_state(status="planned"), generate_new=True
        )
        state = start_image_generation(choice)
        state = record_image_candidate(
            state,
            content_sha256="a" * 64,
            artifact_ref="work/jobs/job-1/candidate.png",
        )

        approved = record_image_approval(
            state,
            reviewer="user",
            recorded_at="2026-08-07T12:00:00+08:00",
            evidence_ref="conversation-message-image-1",
        )

        self.assertEqual("image_approved", approved["status"])
        self.assertTrue(approved["approval"]["image"])
        self.assertFalse(approved["approval"]["preview"])
        self.assertFalse(approved["approval"]["raw"])
        self.assertEqual(
            "a" * 64, approved["approval"]["image_candidate_sha256"]
        )
        self.assertEqual(
            "work/jobs/job-1/candidate.png",
            approved["approval"]["image_artifact_ref"],
        )

    def test_candidate_recording_is_idempotent_and_rejects_conflicts(self):
        choice = record_image_choice(
            create_state(status="planned"), generate_new=True
        )
        state = start_image_generation(choice)
        recorded = record_image_candidate(
            state,
            content_sha256="a" * 64,
            artifact_ref="work/jobs/job-1/candidate.png",
        )

        repeated = record_image_candidate(
            recorded,
            content_sha256="a" * 64,
            artifact_ref="work/jobs/job-1/candidate.png",
        )
        self.assertEqual(recorded, repeated)
        with self.assertRaisesRegex(ValueError, "conflicting candidate image"):
            record_image_candidate(
                recorded,
                content_sha256="b" * 64,
                artifact_ref="work/jobs/job-1/other.png",
            )


class PreviewAndRenderStateTests(unittest.TestCase):
    @staticmethod
    def _image_approved_state():
        return record_original_image_selection(
            record_image_choice(create_state(status="planned"), generate_new=False)
        )

    @staticmethod
    def _real_evidence():
        return {
            "session_status": "generating",
            "progress": 1,
            "video_count": 1,
            "generate_button_visible": False,
            "avatar_bound": True,
            "resource_type": "video",
        }

    def test_preview_choice_is_per_job_and_requires_image_approval(self):
        preview = record_preview_choice(self._image_approved_state(), enabled=True)

        self.assertEqual("preview_choice_recorded", preview["status"])
        self.assertTrue(preview["providers"]["heygen"]["preview_requested"])
        with self.assertRaisesRegex(ValueError, "image_approved"):
            record_preview_choice(create_state(status="planned"), enabled=True)

    def test_blueprint_evidence_cannot_start_rendering(self):
        state = record_preview_choice(self._image_approved_state(), enabled=True)

        with self.assertRaisesRegex(ValueError, "real render evidence"):
            record_render_started(
                state,
                kind="preview",
                evidence={
                    "session_status": "thinking",
                    "progress": 0,
                    "video_count": 0,
                    "generate_button_visible": True,
                    "avatar_bound": False,
                    "resource_type": "blueprint",
                },
            )

    def test_real_preview_render_requires_stable_video_id(self):
        state = record_preview_choice(self._image_approved_state(), enabled=True)

        with self.assertRaisesRegex(ValueError, "video ID"):
            record_render_started(
                state, kind="preview", evidence=self._real_evidence()
            )
        rendering = record_render_started(
            state,
            kind="preview",
            video_id="preview-video-1",
            evidence=self._real_evidence(),
        )

        self.assertEqual("preview_rendering", rendering["status"])
        self.assertEqual(
            "preview-video-1",
            rendering["providers"]["heygen"]["preview_video_id"],
        )

    def test_preview_approval_binds_exact_qa_passed_result(self):
        chosen = record_preview_choice(self._image_approved_state(), enabled=True)
        rendering = record_render_started(
            chosen,
            kind="preview",
            video_id="preview-video-1",
            evidence=self._real_evidence(),
        )
        awaiting = record_preview_result(
            rendering,
            video_id="preview-video-1",
            content_sha256="c" * 64,
            artifact_ref="work/jobs/job-1/preview.mp4",
            qa_passed=True,
        )

        approved = record_preview_approval(
            awaiting,
            reviewer="user",
            recorded_at="2026-08-07T12:10:00+08:00",
            evidence_ref="conversation-message-preview-1",
        )

        self.assertEqual("awaiting_preview_approval", approved["status"])
        self.assertTrue(approved["approval"]["preview"])
        self.assertFalse(approved["approval"]["raw"])
        self.assertEqual(
            "preview-video-1", approved["approval"]["preview_video_id"]
        )
        self.assertEqual("c" * 64, approved["approval"]["preview_artifact_sha256"])

    def test_full_raw_requires_preview_approval_when_requested(self):
        state = record_preview_choice(self._image_approved_state(), enabled=True)
        with self.assertRaisesRegex(ValueError, "preview approval"):
            record_render_started(
                state,
                kind="full_raw",
                video_id="full-video-1",
                evidence=self._real_evidence(),
            )

        no_preview = record_preview_choice(
            self._image_approved_state(), enabled=False
        )
        rendering = record_render_started(
            no_preview,
            kind="full_raw",
            video_id="full-video-1",
            evidence=self._real_evidence(),
        )
        self.assertEqual("full_raw_rendering", rendering["status"])

    def test_full_raw_approval_preserves_other_gates_and_allows_postproduction(self):
        no_preview = record_preview_choice(
            self._image_approved_state(), enabled=False
        )
        rendering = record_render_started(
            no_preview,
            kind="full_raw",
            video_id="full-video-1",
            evidence=self._real_evidence(),
        )
        raw = record_raw_video(
            rendering,
            video_id="full-video-1",
            content_sha256=RAW_SHA256,
            artifact_ref="work/jobs/job-1/full-raw.mp4",
            qa_passed=True,
        )
        awaiting = transition(raw, "awaiting_raw_approval")

        approved = record_raw_approval(
            awaiting,
            reviewer="user",
            recorded_at="2026-08-07T12:20:00+08:00",
            evidence_ref="conversation-message-raw-1",
        )

        self.assertFalse(approved["approval"]["image"])
        self.assertFalse(approved["approval"]["preview"])
        self.assertTrue(approved["approval"]["raw"])
        self.assertEqual(
            "post_production", transition(approved, "post_production")["status"]
        )


class V3StateCliTests(unittest.TestCase):
    def test_cli_records_original_choice_and_real_full_raw_start(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state_path.write_text(
                json.dumps(create_state(status="planned")), encoding="utf-8"
            )
            evidence_path = Path(directory) / "render-evidence.json"
            evidence_path.write_text(
                json.dumps(PreviewAndRenderStateTests._real_evidence()),
                encoding="utf-8",
            )

            commands = (
                ("image-choice", "--use-original"),
                ("preview-choice", "--disabled"),
                (
                    "render-started",
                    "--kind",
                    "full_raw",
                    "--video-id",
                    "full-video-1",
                    "--evidence-json",
                    str(evidence_path),
                ),
            )
            for command in commands:
                with self.subTest(command=command[0]):
                    result = subprocess.run(
                        [sys.executable, str(UPDATE_SCRIPT), str(state_path), *command],
                        cwd=ROOT,
                        capture_output=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(0, result.returncode, result.stderr)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual("full_raw_rendering", state["status"])
            self.assertEqual(
                "original_image1", state["assets"]["job_image"]["source"]
            )
            self.assertFalse(state["providers"]["heygen"]["preview_requested"])

    def test_cli_generated_image_requires_candidate_then_exact_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state_path.write_text(
                json.dumps(create_state(status="planned")), encoding="utf-8"
            )
            commands = (
                ("image-choice", "--generate-new"),
                (
                    "image-candidate",
                    "--sha256",
                    "a" * 64,
                    "--artifact-ref",
                    "work/jobs/job-1/candidate.png",
                ),
                (
                    "approve-image",
                    "--reviewer",
                    "user",
                    "--recorded-at",
                    "2026-08-07T13:00:00+08:00",
                    "--evidence-ref",
                    "conversation-message-image-1",
                ),
            )
            for command in commands:
                result = subprocess.run(
                    [sys.executable, str(UPDATE_SCRIPT), str(state_path), *command],
                    cwd=ROOT,
                    capture_output=True,
                    encoding="utf-8",
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual("image_approved", state["status"])
            self.assertEqual("a" * 64, state["approval"]["image_candidate_sha256"])


class V2MigrationTests(unittest.TestCase):
    @staticmethod
    def _fixture(status):
        return {
            "version": 2,
            "status": status,
            "approval": {"raw": False},
            "providers": {},
            "assets": {},
            "artifacts": {},
            "error": {},
            "retry": {},
        }

    def test_v2_migration_requires_new_image_and_preview_decisions(self):
        old = self._fixture("assets_ready")

        migrated = migrate_v2(old)

        self.assertEqual(3, migrated["version"])
        self.assertEqual("planned", migrated["status"])
        self.assertFalse(migrated["approval"]["image"])
        self.assertFalse(migrated["approval"]["preview"])
        self.assertFalse(migrated["approval"]["raw"])

    def test_v2_migration_preserves_only_schema_valid_stable_assets(self):
        old = self._fixture("assets_ready")
        old["assets"] = {
            "voice": {"voice_id": "voice-1", "alias": "voice1"},
            "identity": {
                "avatar_group_id": "group-1",
                "avatar_look_id": "look-1",
                "alias": "image1",
            },
        }

        migrated = migrate_v2(old)

        self.assertEqual(old["assets"], migrated["assets"])
        self.assertEqual(2, migrated["migration"]["source_version"])


class UpdateStateCliTests(unittest.TestCase):
    def test_updates_atomically_with_exact_backup_and_rejects_unknown_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            original = json.dumps(
                create_state(status="planned"),
                ensure_ascii=False,
            ).encode("utf-8")
            state_path.write_bytes(original)

            result = subprocess.run(
                [
                    sys.executable,
                    str(UPDATE_SCRIPT),
                    str(state_path),
                    "image-choice",
                    "--use-original",
                ],
                cwd=ROOT,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            backups = list(state_path.parent.glob("state.json.*.bak"))
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_bytes())
            updated = json.loads(state_path.read_text(encoding="utf-8"))
            validate_state(updated)
            self.assertEqual("image_approved", updated["status"])
            updated_bytes = state_path.read_bytes()

            rejected = subprocess.run(
                [
                    sys.executable,
                    str(UPDATE_SCRIPT),
                    str(state_path),
                    "image-choice",
                    "--use-original",
                    "--unknown",
                    "value",
                ],
                cwd=ROOT,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertEqual(updated_bytes, state_path.read_bytes())
            self.assertEqual(1, len(list(state_path.parent.glob("state.json.*.bak"))))

    def test_runs_the_complete_recording_sequence_without_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state_path.write_text(
                json.dumps(create_state(status="planned")), encoding="utf-8"
            )
            evidence_path = Path(directory) / "render-evidence.json"
            evidence_path.write_text(
                json.dumps(PreviewAndRenderStateTests._real_evidence()),
                encoding="utf-8",
            )
            commands = (
                ("image-choice", "--use-original"),
                ("preview-choice", "--disabled"),
                (
                    "render-started",
                    "--kind",
                    "full_raw",
                    "--video-id",
                    "video-1",
                    "--evidence-json",
                    str(evidence_path),
                ),
                (
                    "raw-video",
                    "--video-id",
                    "video-1",
                    "--sha256",
                    RAW_SHA256,
                    "--artifact-ref",
                    "outputs/full-raw.mp4",
                    "--qa-passed",
                ),
                ("transition", "--to", "awaiting_raw_approval"),
                (
                    "approve-raw",
                    "--reviewer",
                    "user-owner",
                    "--recorded-at",
                    "2026-08-06T12:00:00+08:00",
                    "--evidence-ref",
                    "conversation-message-42",
                ),
            )
            for command in commands:
                with self.subTest(command=command[0]):
                    result = subprocess.run(
                        [sys.executable, str(UPDATE_SCRIPT), str(state_path), *command],
                        cwd=ROOT,
                        capture_output=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(0, result.returncode, result.stderr)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            validate_state(state)
            self.assertEqual("awaiting_raw_approval", state["status"])
            self.assertIs(True, state["approval"]["raw"])
            self.assertNotIn("url", json.dumps(state, ensure_ascii=False).lower())


class InitStateCliTests(unittest.TestCase):
    def test_creates_current_heygen_only_v3_state(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "state.json"
            result = subprocess.run(
                [sys.executable, str(INIT_SCRIPT), "--out", str(output)],
                cwd=ROOT,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            state = json.loads(output.read_text(encoding="utf-8"))
            validate_state(state)
            self.assertEqual(create_state(), state)
            serialized = json.dumps(state, ensure_ascii=False).lower()
            self.assertNotIn("minimax", serialized)
            self.assertNotIn("api_key", serialized)


class StateMigrationArchitectureTests(unittest.TestCase):
    def test_unknown_legacy_values_are_never_embedded(self):
        values = (
            "Authorization: Bearer arbitrary",
            "authorization and signature are documentation labels",
            "https://[malformed",
            "sk-SK",
            "sk-api-arbitrary-secret-looking-value",
        )
        fingerprints = set()
        for value in values:
            with self.subTest(value=value):
                new = migrate_v1({"status": "created", "unknown": value})
                serialized = json.dumps(new, ensure_ascii=False)
                self.assertNotIn(value, serialized)
                self.assertNotIn("legacy", new)
                self.assertNotIn("unknown", new)
                self.assertEqual(
                    "caller-managed", new["migration"]["legacy_preservation"]
                )
                self.assertEqual(1, new["migration"]["unmapped_field_count"])
                fingerprints.add(new["migration"]["source_sha256"])
        self.assertEqual(len(values), len(fingerprints))

    def test_direct_migration_uses_canonical_json_fingerprint(self):
        old = {"status": "created", "custom": {"nested": [1, True]}}
        canonical = json.dumps(
            old,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

        new = migrate_v1(old)

        self.assertEqual(
            {
                "source_version": 1,
                "source_sha256": hashlib.sha256(canonical).hexdigest(),
                "fingerprint_basis": "canonical-json",
                "unmapped_field_count": 2,
                "legacy_preservation": "caller-managed",
                "legacy_embedded": False,
            },
            new["migration"],
        )

    def test_allowlisted_provider_ids_reject_non_ids_without_leaking_values(self):
        invalid = (
            "Authorization: Bearer arbitrary",
            "https://example.com/video",
            "contains whitespace",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "provider ID") as caught:
                    migrate_v1({"heygen": {"preview_video_id": value}})
                self.assertNotIn(value, str(caught.exception))

    def test_minimax_voice_ids_are_never_relabelled_as_heygen(self):
        for voice_id in ("Voice001", "sk-brand_voice_2026", "arbitrary-old-id"):
            with self.subTest(voice_id=voice_id):
                migrated = migrate_v1({"minimax": {"voice_id": voice_id}})
                self.assertEqual({}, migrated["assets"])
                self.assertNotIn(voice_id, json.dumps(migrated, ensure_ascii=False))

    def test_heygen_preview_id_uses_opaque_id_safety_not_minimax_format(self):
        for preview_id in ("v", "sk-preview-01", "视频预览-1"):
            with self.subTest(preview_id=preview_id):
                migrated = migrate_v1(
                    {"heygen": {"preview_video_id": preview_id}}
                )
                self.assertEqual(
                    preview_id,
                    migrated["providers"]["heygen"]["preview_video_id"],
                )

        for preview_id in (
            "Bearer preview",
            "Authorization: Bearer preview",
            "https://example.com/video",
            " preview-1",
            "preview\n1",
        ):
            with self.subTest(preview_id=preview_id):
                with self.assertRaisesRegex(ValueError, "heygen preview provider ID"):
                    migrate_v1({"heygen": {"preview_video_id": preview_id}})

    def test_v2_state_rejects_legacy_and_unknown_top_level_fields(self):
        for field in ("legacy", "metadata", "api_key", "authorization"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "unsupported state field"):
                    validate_state({"version": 2, "status": "created", field: {}})

    def test_v2_migration_rejects_insecure_state_instead_of_stripping_it(self):
        insecure = {
            "version": 2,
            "status": "created",
            "api_key": "arbitrary value",
        }

        with self.assertRaisesRegex(ValueError, "unsupported state field"):
            migrate_v1(insecure)


class StateMigrationTests(unittest.TestCase):
    def test_migration_preserves_only_safe_heygen_preview_id(self):
        old = {
            "heygen": {"preview_video_id": "video-1", "photo_avatar_id": "avatar-1"},
            "minimax": {"voice_id": "Voice001", "audio_job_id": "audio-1"},
        }

        new = migrate_v1(old)

        self.assertEqual("video-1", new["providers"]["heygen"]["preview_video_id"])
        self.assertEqual({}, new["assets"])
        self.assertNotIn("Voice001", json.dumps(new, ensure_ascii=False))
        self.assertNotIn("photo_avatar_id", new["providers"]["heygen"])
        self.assertNotIn("minimax", new["providers"])

    def test_migration_does_not_mutate_input(self):
        old = {
            "status": "raw_qa",
            "raw_approved": False,
            "heygen": {"preview_video_id": "video-1"},
        }
        original = copy.deepcopy(old)

        migrate_v1(old)

        self.assertEqual(original, old)

    def test_migration_drops_non_allowlisted_legacy_sections(self):
        old = {
            "status": "image_ready",
            "providers": {"image": {"asset_id": "image-1"}},
            "assets": {"identity": {"alias": "image1"}},
            "artifacts": {"audio": "产物/声音.mp3"},
            "error": {"stage": "image", "reason": "timeout"},
            "retry": {"image": 2},
        }

        new = migrate_v1(old)

        self.assertEqual("planned", new["status"])
        self.assertEqual({}, new["providers"])
        self.assertEqual({}, new["assets"])
        for field in ("artifacts", "error", "retry"):
            self.assertNotIn(field, new)

    def test_migration_never_embeds_unknown_legacy_data(self):
        old = {
            "status": "created",
            "custom": {"中文字段": [1, {"nested": True}]},
            "future_provider": {"job_ref": "future-1"},
        }

        new = migrate_v1(old)

        self.assertNotIn("legacy", new)
        self.assertNotIn("custom", new)
        self.assertNotIn("future_provider", new)

    def test_migration_requires_reapproval_for_legacy_unbound_raw_approval(self):
        approved = migrate_v1({"status": "awaiting_raw_approval", "raw_approved": True})
        self.assertIs(False, approved["approval"]["raw"])
        self.assertEqual("planned", approved["status"])

        postproduction = migrate_v1({"status": "post_production", "raw_approved": True})
        self.assertIs(False, postproduction["approval"]["raw"])
        self.assertEqual("planned", postproduction["status"])

        for value in ("true", "false", 1, 0):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "raw approval"):
                    migrate_v1({"raw_approved": value})

    def test_migration_rejects_invalid_input_and_status(self):
        for old in ([], None, {"status": "obsolete"}, {"heygen": []}):
            with self.subTest(old=old):
                with self.assertRaises(ValueError):
                    migrate_v1(old)

    def test_migration_result_is_a_valid_version_three_state(self):
        new = migrate_v1({"status": "planned"})

        validate_state(new)
        self.assertEqual(3, new["version"])
        self.assertEqual("planned", new["status"])
        self.assertIs(False, new["approval"]["raw"])

    def test_migration_accepts_absent_version_one_two_or_three(self):
        self.assertEqual(3, migrate_v1({"status": "created"})["version"])
        self.assertEqual(
            3, migrate_v1({"version": 1, "status": "created"})["version"]
        )
        version_two = {
            "version": 2,
            "status": "created",
            "approval": {"raw": False},
            "providers": {"heygen": {"video_id": "video-1"}},
        }
        migrated = migrate_v1(version_two)
        self.assertEqual(3, migrated["version"])
        self.assertEqual("created", migrated["status"])
        self.assertIsNot(version_two, migrated)

        version_three = {"version": 3, "status": "created"}
        copied = migrate_v1(version_three)
        self.assertEqual(version_three, copied)
        self.assertIsNot(version_three, copied)

        invalid_versions = (0, 4, -1, True, False, "SENSITIVE_VERSION", 1.0)
        for version in invalid_versions:
            with self.subTest(version=version):
                with self.assertRaisesRegex(
                    ValueError, "unsupported state version"
                ) as caught:
                    migrate_v1({"version": version, "status": "created"})
                self.assertNotIn(str(version), str(caught.exception))

    def test_migration_rejects_nonfinite_known_and_unknown_legacy_metadata(self):
        cases = (
            {"status": "created", "retry": {"delay_seconds": float("nan")}},
            {"status": "created", "custom": {"score": float("inf")}},
            {"status": "created", "custom": [float("-inf")]},
        )
        for old in cases:
            with self.subTest(old=old):
                with self.assertRaisesRegex(ValueError, "standard JSON"):
                    migrate_v1(old)

    def test_migration_rejects_non_string_keys_and_nonstandard_containers(self):
        invalid_legacy = (
            {"status": "created", "metadata": {1: "would stringify"}},
            {"status": "created", "metadata": ("would become a list",)},
        )
        for old in invalid_legacy:
            with self.subTest(old=old):
                with self.assertRaisesRegex(ValueError, "standard JSON"):
                    migrate_v1(old)


class MigrateStateCliTests(unittest.TestCase):
    def test_default_writes_new_sibling_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "任务状态.json"
            original = self._write_source(source)

            result = self._run_cli(source)

            output = source.with_name("任务状态.migrated.json")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(str(output), result.stdout.strip())
            self.assertEqual(original, source.read_bytes())
            self.assertTrue(output.exists())
            self.assertEqual(3, json.loads(output.read_text(encoding="utf-8"))["version"])

    def test_accepts_utf8_bom_and_writes_bomless_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            source.write_text(
                json.dumps({"status": "created", "note": "中文"}, ensure_ascii=False),
                encoding="utf-8-sig",
            )

            result = self._run_cli(source)

            output = source.with_name("job-state.migrated.json")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(output.read_bytes().startswith(b"\xef\xbb\xbf"))
            migrated = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("note", migrated)
            self.assertEqual(
                "exact-source-bytes", migrated["migration"]["fingerprint_basis"]
            )
            self.assertEqual(
                "original-source", migrated["migration"]["legacy_preservation"]
            )

    def test_explicit_output_is_supported_and_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            self._write_source(source)
            output = Path(directory) / "子目录" / "new-state.json"

            first = self._run_cli(source, "--output", output)
            original_output = output.read_bytes()
            second = self._run_cli(source, "--output", output)

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertNotEqual(0, second.returncode)
            self.assertIn("refusing to overwrite", second.stderr)
            self.assertEqual(original_output, output.read_bytes())

    def test_in_place_creates_exact_timestamped_backup_and_replaces_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "任务.json"
            original = self._write_source(source)

            result = self._run_cli(source, "--in-place")

            backups = list(source.parent.glob(f"{source.name}.*.bak"))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(str(source), result.stdout.strip())
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_bytes())
            self.assertEqual(3, json.loads(source.read_text(encoding="utf-8"))["version"])
            self.assertFalse(source.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_backup_name_collision_gets_a_numeric_suffix(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            original = self._write_source(source)
            module = self._load_cli_module()
            first_backup = source.with_name(f"{source.name}.20260806T120000000000.bak")
            first_backup.write_bytes(b"existing backup")

            with patch.object(module, "_timestamp", return_value="20260806T120000000000"):
                with redirect_stdout(StringIO()):
                    result = module.main([str(source), "--in-place"])

            second_backup = source.with_name(
                f"{source.name}.20260806T120000000000-1.bak"
            )
            self.assertEqual(0, result)
            self.assertEqual(b"existing backup", first_backup.read_bytes())
            self.assertEqual(original, second_backup.read_bytes())

    def test_invalid_json_and_invalid_state_create_no_outputs_or_backups(self):
        cases = (b"{not json", json.dumps({"status": "unknown"}).encode("utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            for index, contents in enumerate(cases):
                with self.subTest(index=index):
                    source = Path(directory) / f"bad-{index}.json"
                    source.write_bytes(contents)
                    before = sorted(path.name for path in source.parent.iterdir())

                    default_result = self._run_cli(source)
                    in_place_result = self._run_cli(source, "--in-place")

                    self.assertNotEqual(0, default_result.returncode)
                    self.assertNotEqual(0, in_place_result.returncode)
                    self.assertEqual(contents, source.read_bytes())
                    self.assertEqual(before, sorted(path.name for path in source.parent.iterdir()))

    def test_invalid_state_value_is_not_copied_to_error_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            secret_marker = "SENSITIVE_LEGACY_VALUE"
            source.write_text(
                json.dumps({"status": secret_marker}), encoding="utf-8"
            )

            result = self._run_cli(source)

            self.assertNotEqual(0, result.returncode)
            self.assertNotIn(secret_marker, result.stderr)

    def test_unsupported_version_default_failure_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            contents = b'{"version":4,"status":"created"}'
            source.write_bytes(contents)

            result = self._run_cli(source)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("unsupported state version", result.stderr)
            self.assertEqual(contents, source.read_bytes())
            self.assertEqual(
                [source.name], [path.name for path in source.parent.iterdir()]
            )

    def test_unsupported_version_in_place_failure_does_not_backup_or_replace(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            secret_marker = "SENSITIVE_VERSION_VALUE"
            contents = json.dumps(
                {"version": secret_marker, "status": "created"}
            ).encode("utf-8")
            source.write_bytes(contents)

            result = self._run_cli(source, "--in-place")

            self.assertNotEqual(0, result.returncode)
            self.assertNotIn(secret_marker, result.stderr)
            self.assertEqual(contents, source.read_bytes())
            self.assertEqual(
                [source.name], [path.name for path in source.parent.iterdir()]
            )

    def test_nonfinite_json_default_failure_does_not_write(self):
        for constant in (b"NaN", b"Infinity", b"-Infinity"):
            with self.subTest(constant=constant):
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "job-state.json"
                    contents = (
                        b'{"status":"created","custom":{"nested":['
                        + constant
                        + b"]}}"
                    )
                    source.write_bytes(contents)

                    result = self._run_cli(source)

                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("non-finite", result.stderr)
                    self.assertEqual(contents, source.read_bytes())
                    self.assertEqual(
                        [source.name], [path.name for path in source.parent.iterdir()]
                    )

    def test_nonfinite_json_in_place_failure_does_not_backup_or_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            contents = b'{"status":"created","retry":{"delay":NaN}}'
            source.write_bytes(contents)

            result = self._run_cli(source, "--in-place")

            self.assertNotEqual(0, result.returncode)
            self.assertIn("non-finite", result.stderr)
            self.assertEqual(contents, source.read_bytes())
            self.assertEqual(
                [source.name], [path.name for path in source.parent.iterdir()]
            )

    def test_nonfinite_migration_result_is_not_serialized_or_written(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            source.write_text('{"status":"created"}', encoding="utf-8")
            module = self._load_cli_module()
            unsafe_result = {
                "version": 2,
                "status": "created",
                "approval": {"raw": False},
                "legacy": {"score": float("nan")},
            }

            with patch.object(module, "migrate_v1", return_value=unsafe_result):
                with redirect_stdout(StringIO()), redirect_stderr(
                    StringIO()
                ) as errors:
                    result = module.main([str(source)])

            self.assertNotEqual(0, result)
            self.assertIn("standard JSON", errors.getvalue())
            self.assertEqual(
                [source.name], [path.name for path in source.parent.iterdir()]
            )

    def test_unknown_header_default_is_excluded_and_source_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            marker = "SENSITIVE_CLI_KEY_VALUE"
            contents = json.dumps(
                {
                    "status": "created",
                    "metadata": {"nested": [{"API_KEY": marker}]},
                }
            ).encode("utf-8")
            source.write_bytes(contents)

            result = self._run_cli(source)

            output = source.with_name("job-state.migrated.json")
            migrated = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(contents, source.read_bytes())
            self.assertNotIn(marker, output.read_text(encoding="utf-8"))
            self.assertEqual(
                hashlib.sha256(contents).hexdigest(),
                migrated["migration"]["source_sha256"],
            )

    def test_unknown_signed_url_in_place_is_excluded_and_backed_up_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            marker = "SENSITIVE_CLI_URL_VALUE"
            signed_url = (
                "https://cdn.example.com/video.mp4?"
                f"X-Goog-Signature={marker}&X-Goog-Credential=account"
            )
            contents = json.dumps(
                {"status": "created", "download_url": signed_url}
            ).encode("utf-8")
            source.write_bytes(contents)

            result = self._run_cli(source, "--in-place")

            backups = list(source.parent.glob(f"{source.name}.*.bak"))
            migrated = json.loads(source.read_text(encoding="utf-8"))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(1, len(backups))
            self.assertEqual(contents, backups[0].read_bytes())
            self.assertNotIn(marker, source.read_text(encoding="utf-8"))
            self.assertEqual(
                "exact-byte-backup", migrated["migration"]["legacy_preservation"]
            )

    def test_unknown_malformed_url_uses_the_same_external_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            marker = "SENSITIVE_CLI_MALFORMED_URL_VALUE"
            malformed = "https://example.com／" + marker + "?ordinary=value"
            contents = json.dumps(
                {"status": "created", "metadata": {"download": malformed}},
                ensure_ascii=False,
            ).encode("utf-8")
            source.write_bytes(contents)

            result = self._run_cli(source, "--in-place")

            backups = list(source.parent.glob(f"{source.name}.*.bak"))
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(1, len(backups))
            self.assertEqual(contents, backups[0].read_bytes())
            self.assertNotIn(marker, source.read_text(encoding="utf-8"))

    def test_duplicate_json_key_default_failure_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            contents = (
                b'{"status":"created","metadata":'
                b'{"provider_id":"first","provider_id":"second"}}'
            )
            source.write_bytes(contents)

            result = self._run_cli(source)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("duplicate JSON object key", result.stderr)
            self.assertNotIn("first", result.stderr)
            self.assertNotIn("second", result.stderr)
            self.assertEqual(contents, source.read_bytes())
            self.assertEqual(
                [source.name], [path.name for path in source.parent.iterdir()]
            )

    def test_in_place_detects_concurrent_content_change_after_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            original = self._write_source(source)
            concurrent_marker = "CONCURRENT_SENSITIVE_NEW_BYTES"
            concurrent = concurrent_marker.encode("utf-8")
            module = self._load_cli_module()
            real_backup = module._backup_source

            def backup_then_change(path, contents):
                backup = real_backup(path, contents)
                path.write_bytes(concurrent)
                return backup

            with patch.object(module, "_backup_source", side_effect=backup_then_change):
                with redirect_stdout(StringIO()), redirect_stderr(
                    StringIO()
                ) as errors:
                    result = module.main([str(source), "--in-place"])

            backups = list(source.parent.glob(f"{source.name}.*.bak"))
            self.assertNotEqual(0, result)
            self.assertIn("source changed", errors.getvalue())
            self.assertNotIn(concurrent_marker, errors.getvalue())
            self.assertEqual(concurrent, source.read_bytes())
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_bytes())
            self.assertFalse(list(source.parent.glob("*.tmp")))

    def test_in_place_detects_concurrent_metadata_change_after_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            original = self._write_source(source)
            module = self._load_cli_module()
            real_backup = module._backup_source

            def backup_then_touch(path, contents):
                backup = real_backup(path, contents)
                current = path.stat()
                os.utime(
                    path,
                    ns=(current.st_atime_ns, current.st_mtime_ns + 2_000_000_000),
                )
                return backup

            with patch.object(module, "_backup_source", side_effect=backup_then_touch):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    result = module.main([str(source), "--in-place"])

            backups = list(source.parent.glob(f"{source.name}.*.bak"))
            self.assertNotEqual(0, result)
            self.assertEqual(original, source.read_bytes())
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_bytes())

    def test_default_creation_does_not_depend_on_hard_links(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            self._write_source(source)
            module = self._load_cli_module()

            with patch.object(
                module.os, "link", side_effect=OSError("hard links unavailable")
            ):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    result = module.main([str(source)])

            output = source.with_name("job-state.migrated.json")
            self.assertEqual(0, result)
            self.assertEqual(3, json.loads(output.read_text(encoding="utf-8"))["version"])

    def test_symlink_source_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            source = Path(directory) / "job-state.json"
            original = self._write_source(target)
            try:
                source.symlink_to(target)
            except OSError:
                module = self._load_cli_module()
                with patch.object(module.Path, "is_symlink", return_value=True):
                    with redirect_stdout(StringIO()), redirect_stderr(
                        StringIO()
                    ) as errors:
                        return_code = module.main([str(source)])
                error_output = errors.getvalue()
            else:
                result = self._run_cli(source)
                return_code = result.returncode
                error_output = result.stderr

            self.assertNotEqual(0, return_code)
            self.assertIn("symbolic link", error_output)
            self.assertEqual(original, target.read_bytes())
            self.assertFalse(source.with_name("job-state.migrated.json").exists())

    def test_help_and_argument_conflict_do_not_mutate_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "job-state.json"
            original = self._write_source(source)

            help_result = subprocess.run(
                [sys.executable, str(MIGRATE_SCRIPT), "--help"],
                cwd=directory,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            conflict_result = self._run_cli(
                source, "--output", Path(directory) / "out.json", "--in-place"
            )

            self.assertEqual(0, help_result.returncode, help_result.stderr)
            self.assertIn("--in-place", help_result.stdout)
            self.assertNotEqual(0, conflict_result.returncode)
            self.assertEqual(original, source.read_bytes())
            self.assertEqual([source.name], [path.name for path in source.parent.iterdir()])

    @staticmethod
    def _write_source(path):
        contents = json.dumps(
            {
                "status": "planned",
                "raw_approved": False,
                "heygen": {"preview_video_id": "video-1"},
                "minimax": {"voice_id": "Voice001"},
                "artifact": "音频/旁白.mp3",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        path.write_bytes(contents)
        return contents

    @staticmethod
    def _run_cli(source, *extra_args):
        return subprocess.run(
            [sys.executable, str(MIGRATE_SCRIPT), str(source), *(str(arg) for arg in extra_args)],
            cwd=ROOT,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    @staticmethod
    def _load_cli_module():
        scripts_path = str(ROOT / "scripts")
        sys.path.insert(0, scripts_path)
        try:
            sys.modules.pop("migrate_job_state", None)
            return importlib.import_module("migrate_job_state")
        finally:
            sys.path.remove(scripts_path)


if __name__ == "__main__":
    unittest.main()
