"""Versioned, resumable state for the digital-human production workflow."""

import hashlib
import json
import math
import re
import unicodedata
from copy import deepcopy
from datetime import datetime


STATES = (
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
)

_STATE_INDEX = {name: index for index, name in enumerate(STATES)}
ALLOWED_TRANSITIONS = {
    "created": {"planned"},
    "planned": {"image_generation_choice_recorded"},
    "image_generation_choice_recorded": {
        "awaiting_image_approval",
        "image_approved",
    },
    "awaiting_image_approval": {"image_approved"},
    "image_approved": {"preview_choice_recorded"},
    "preview_choice_recorded": {"preview_rendering", "full_raw_rendering"},
    "preview_rendering": {"awaiting_preview_approval"},
    "awaiting_preview_approval": {"full_raw_rendering"},
    "full_raw_rendering": {"raw_qa"},
    "raw_qa": {"awaiting_raw_approval"},
    "awaiting_raw_approval": {"post_production"},
    "post_production": {"final_qa"},
    "final_qa": {"complete"},
}
_ALLOWED_STATE_FIELDS = frozenset(
    {
        "version",
        "status",
        "approval",
        "providers",
        "assets",
        "artifacts",
        "error",
        "retry",
        "migration",
    }
)
_OBJECT_FIELDS = ("providers", "assets", "artifacts", "error", "retry", "migration")
_PROVIDER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}")
_URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RFC3339_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)\Z"
)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"[A-Za-z]:[\\/]")
_LOCAL_FILE_REFERENCE = re.compile(r"(?:^|[\\/])[^\\/]+\.[A-Za-z0-9]{1,16}\Z")
_SENSITIVE_REFERENCE = re.compile(
    r"(?<![a-z0-9_-])(?:[a-z0-9]+[-_])*"
    r"(?:access[-_]?token|refresh[-_]?token|token|api[-_]?key|authorization|"
    r"cookie|credential|signature)\s*[=:]\s*\S+",
    re.IGNORECASE,
)
_CREDENTIAL_SCHEME_REFERENCE = re.compile(r"(?:basic|bearer)\s+\S+", re.IGNORECASE)
_JWT_REFERENCE = re.compile(
    r"eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)
_SECRET_PREFIX_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}", re.IGNORECASE
)
_APPROVAL_FIELDS = frozenset(
    {
        "image",
        "preview",
        "raw",
        "image_reviewer",
        "image_candidate_sha256",
        "image_artifact_ref",
        "image_recorded_at",
        "image_evidence_ref",
        "preview_reviewer",
        "preview_artifact_sha256",
        "preview_video_id",
        "preview_recorded_at",
        "preview_evidence_ref",
        "reviewer",
        "raw_artifact_sha256",
        "heygen_video_id",
        "recorded_at",
        "evidence_ref",
    }
)
_RAW_ARTIFACT_FIELDS = frozenset({"kind", "sha256", "qa_passed", "ref"})
_AUDIO_ARTIFACT_FIELDS = frozenset({"sha256", "duration_seconds"})
_IMAGE_CANDIDATE_FIELDS = frozenset({"sha256", "ref"})
_VIDEO_ARTIFACT_FIELDS = frozenset({"kind", "sha256", "qa_passed", "ref"})
_RENDER_START_FIELDS = frozenset({"video_id", "evidence"})
_RENDER_EVIDENCE_FIELDS = frozenset(
    {
        "session_status",
        "progress",
        "video_count",
        "generate_button_visible",
        "avatar_bound",
        "resource_type",
    }
)
_MIGRATION_BASES = frozenset({"canonical-json", "exact-source-bytes"})
_PRESERVATION_STRATEGIES = frozenset(
    {"caller-managed", "original-source", "exact-byte-backup"}
)
AUTO_REVIEWER = "auto-mode"
AUTO_JOB_ROUTE = {
    "operating_mode": "auto",
    "voice_provider": "minimax",
    "material_route": "none",
}


def validate_state(state) -> None:
    """Reject malformed or out-of-schema state without changing it."""
    if not isinstance(state, dict):
        raise ValueError("state must be a JSON object")
    _require_standard_json(state, "state")
    try:
        json.dumps(state, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("state must contain only standard JSON values") from error

    if set(state) - _ALLOWED_STATE_FIELDS:
        raise ValueError("unsupported state field")

    status = state.get("status")
    if not isinstance(status, str) or status not in _STATE_INDEX:
        raise ValueError("unknown state status")

    if "version" in state and (
        type(state["version"]) is not int or state["version"] != 3
    ):
        raise ValueError("state version must be 3")

    approval = state.get("approval")
    if approval is not None and not isinstance(approval, dict):
        raise ValueError("approval must be a JSON object")
    if isinstance(approval, dict):
        if set(approval) - _APPROVAL_FIELDS:
            raise ValueError("unsupported approval field")
        for approval_type in ("image", "preview", "raw"):
            if approval_type in approval and type(approval[approval_type]) is not bool:
                raise ValueError(f"{approval_type} approval must be a boolean")

    for field in _OBJECT_FIELDS:
        if field in state and not isinstance(state[field], dict):
            raise ValueError(f"{field} must be a JSON object")

    if "providers" in state:
        _validate_providers(state["providers"])
    if "assets" in state:
        _validate_assets(state["assets"])
    if "artifacts" in state:
        _validate_artifacts(state["artifacts"])
    if "migration" in state:
        _validate_migration(state["migration"])

    if isinstance(approval, dict) and approval.get("raw") is True:
        _require_bound_raw_approval(state)
    if isinstance(approval, dict) and approval.get("image") is True:
        _require_bound_image_approval(state)
    if isinstance(approval, dict) and approval.get("preview") is True:
        _require_bound_preview_approval(state)
    if status in {"preview_rendering", "full_raw_rendering"}:
        kind = "preview" if status == "preview_rendering" else "full_raw"
        _require_recorded_render_start(state, kind)
    if _STATE_INDEX[status] >= _STATE_INDEX["post_production"]:
        _require_bound_raw_approval(state)


def create_state(*, status="created") -> dict:
    """Return a fresh valid v3 state with no external work recorded."""
    state = {
        "version": 3,
        "status": status,
        "approval": {"image": False, "preview": False, "raw": False},
        "providers": {},
        "assets": {},
        "artifacts": {},
        "error": {},
        "retry": {},
    }
    validate_state(state)
    return state


def transition(state, target):
    """Return a deep-copied state advanced by one explicitly allowed edge."""
    validate_state(state)
    if not isinstance(target, str) or target not in _STATE_INDEX:
        raise ValueError("unknown target state")

    if target == "post_production":
        _require_bound_raw_approval(state)
    if target == "awaiting_raw_approval" and state["status"] != target:
        _require_qa_passed_raw(state)

    current = state["status"]
    if target == current:
        return deepcopy(state)
    if target in {"preview_rendering", "full_raw_rendering"}:
        raise ValueError("real render evidence is required before rendering")
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        if _STATE_INDEX[target] < _STATE_INDEX[current]:
            raise ValueError(
                f"backward transition is not allowed: {current} -> {target}"
            )
        raise ValueError(
            f"cannot skip states: {current} -> {target}"
        )

    result = deepcopy(state)
    result["status"] = target
    validate_state(result)
    return result


def record_image_choice(state, *, generate_new):
    """Record the job's explicit image-generation choice."""
    validate_state(state)
    _require_recording_status(
        state, "planned", "image_generation_choice_recorded"
    )
    if type(generate_new) is not bool:
        raise ValueError("image generation choice must be a boolean")
    job_image = {
        "identity_master_alias": "image1",
        "generate_new": generate_new,
        "source": "pending",
    }
    result = deepcopy(state)
    assets = result.setdefault("assets", {})
    _require_matching_or_absent(
        assets, "job_image", job_image, "image generation choice"
    )
    assets["job_image"] = job_image
    result["status"] = "image_generation_choice_recorded"
    validate_state(result)
    return result


def record_original_image_selection(state):
    """Select the original image1 when the user declines image generation."""
    validate_state(state)
    _require_recording_status(
        state, "image_generation_choice_recorded", "image_approved"
    )
    job_image = _require_job_image(state)
    if job_image["generate_new"] is not False:
        raise ValueError("original image selection requires generate_new=False")
    expected = deepcopy(job_image)
    expected["source"] = "original_image1"
    result = deepcopy(state)
    current = result["assets"]["job_image"]
    if current not in (job_image, expected):
        raise ValueError("conflicting original image selection")
    result["assets"]["job_image"] = expected
    result["status"] = "image_approved"
    validate_state(result)
    return result


def start_image_generation(state):
    """Open the exact-candidate approval gate for a generated job image."""
    validate_state(state)
    _require_recording_status(
        state, "image_generation_choice_recorded", "awaiting_image_approval"
    )
    job_image = _require_job_image(state)
    if job_image["generate_new"] is not True:
        raise ValueError("image generation requires generate_new=True")
    result = deepcopy(state)
    result["status"] = "awaiting_image_approval"
    validate_state(result)
    return result


def record_image_candidate(state, *, content_sha256, artifact_ref):
    """Record the sole generated image candidate for this job."""
    validate_state(state)
    _require_recording_status(
        state, "awaiting_image_approval", "awaiting_image_approval"
    )
    if _require_job_image(state)["generate_new"] is not True:
        raise ValueError("candidate image requires generate_new=True")
    _require_sha256(content_sha256, "candidate image")
    _require_stable_reference(
        artifact_ref, "candidate image reference", allow_local_file=True
    )
    candidate = {"sha256": content_sha256, "ref": artifact_ref}
    result = deepcopy(state)
    artifacts = result.setdefault("artifacts", {})
    try:
        _require_matching_or_absent(
            artifacts, "image_candidate", candidate, "candidate image"
        )
    except ValueError as error:
        raise ValueError("conflicting candidate image") from error
    artifacts["image_candidate"] = candidate
    validate_state(result)
    return result


def record_image_approval(state, *, reviewer, recorded_at, evidence_ref):
    """Bind explicit user approval to the exact generated image candidate."""
    validate_state(state)
    _require_recording_status(
        state, "awaiting_image_approval", "image_approved"
    )
    candidate = state.get("artifacts", {}).get("image_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("candidate image is required before approval")
    _validate_artifacts({"image_candidate": candidate})
    _reject_auto_reviewer(reviewer)
    _require_evidence_text(reviewer, "image approval evidence")
    _require_approval_timestamp(recorded_at, label="image approval")
    _require_opaque_reference(evidence_ref, "image approval reference")
    result = deepcopy(state)
    approval = result.setdefault("approval", {})
    expected = {
        "image": True,
        "image_reviewer": reviewer,
        "image_candidate_sha256": candidate["sha256"],
        "image_artifact_ref": candidate["ref"],
        "image_recorded_at": recorded_at,
        "image_evidence_ref": evidence_ref,
    }
    for field, value in expected.items():
        if field == "image" and approval.get(field) is False:
            approval[field] = value
            continue
        _require_matching_or_absent(approval, field, value, "image approval")
        approval[field] = value
    result["assets"]["job_image"]["source"] = "generated_candidate"
    result["status"] = "image_approved"
    validate_state(result)
    return result


def record_preview_choice(state, *, enabled):
    """Record whether this job requires a 15-second preview."""
    validate_state(state)
    _require_recording_status(state, "image_approved", "preview_choice_recorded")
    if type(enabled) is not bool:
        raise ValueError("preview choice must be a boolean")
    result = deepcopy(state)
    heygen = result.setdefault("providers", {}).setdefault("heygen", {})
    _require_matching_or_absent(
        heygen, "preview_requested", enabled, "preview choice"
    )
    heygen["preview_requested"] = enabled
    result["status"] = "preview_choice_recorded"
    validate_state(result)
    return result


def apply_auto_defaults(state):
    """Lock auto-mode route defaults and skip image/preview confirmation gates."""
    validate_state(state)
    if state["status"] == "preview_choice_recorded":
        _require_matching_auto_defaults(state)
        return deepcopy(state)
    if state["status"] != "planned":
        raise ValueError("event requires planned or preview_choice_recorded status")
    result = deepcopy(state)
    assets = result.setdefault("assets", {})
    _require_matching_or_absent(assets, "job_route", AUTO_JOB_ROUTE, "job route")
    assets["job_route"] = dict(AUTO_JOB_ROUTE)
    validate_state(result)
    chosen = record_image_choice(result, generate_new=False)
    selected = record_original_image_selection(chosen)
    return record_preview_choice(selected, enabled=False)


def record_render_started(state, *, kind, evidence, video_id=None):
    """Record only browser evidence that proves HeyGen actually started rendering."""
    validate_state(state)
    if kind not in {"preview", "full_raw"}:
        raise ValueError("render kind must be preview or full_raw")
    _require_real_render_evidence(evidence)
    _require_provider_id(video_id, "HeyGen video ID")
    requested = _preview_requested(state)
    if kind == "preview":
        _require_recording_status(
            state, "preview_choice_recorded", "preview_rendering"
        )
        if requested is not True:
            raise ValueError("preview rendering requires preview_requested=True")
        status = "preview_rendering"
        provider_field = "preview_video_id"
        artifact_field = "preview_render_start"
    else:
        if requested is True:
            if state["status"] != "awaiting_preview_approval":
                raise ValueError("preview approval is required before full raw")
            _require_bound_preview_approval(state)
        else:
            _require_recording_status(
                state, "preview_choice_recorded", "full_raw_rendering"
            )
        status = "full_raw_rendering"
        provider_field = "video_id"
        artifact_field = "full_raw_render_start"

    result = deepcopy(state)
    heygen = result.setdefault("providers", {}).setdefault("heygen", {})
    _require_matching_or_absent(heygen, provider_field, video_id, "video ID")
    heygen[provider_field] = video_id
    render_start = {"video_id": video_id, "evidence": deepcopy(evidence)}
    artifacts = result.setdefault("artifacts", {})
    _require_matching_or_absent(
        artifacts, artifact_field, render_start, "render start evidence"
    )
    artifacts[artifact_field] = render_start
    result["status"] = status
    validate_state(result)
    return result


def record_preview_result(
    state,
    *,
    video_id,
    content_sha256,
    artifact_ref,
    qa_passed,
):
    """Record the exact rendered preview and advance to its approval gate."""
    validate_state(state)
    _require_recording_status(
        state, "preview_rendering", "awaiting_preview_approval"
    )
    _require_provider_id(video_id, "HeyGen preview video ID")
    _require_sha256(content_sha256, "preview artifact")
    if type(qa_passed) is not bool:
        raise ValueError("preview artifact QA result must be a boolean")
    _require_stable_reference(
        artifact_ref, "preview artifact reference", allow_local_file=True
    )
    result = deepcopy(state)
    heygen = result.setdefault("providers", {}).setdefault("heygen", {})
    _require_matching_or_absent(
        heygen, "preview_video_id", video_id, "preview video ID"
    )
    preview_video = {
        "kind": "preview",
        "sha256": content_sha256,
        "qa_passed": qa_passed,
        "ref": artifact_ref,
    }
    artifacts = result.setdefault("artifacts", {})
    _require_matching_or_absent(
        artifacts, "preview_video", preview_video, "preview video artifact"
    )
    artifacts["preview_video"] = preview_video
    result["status"] = "awaiting_preview_approval"
    validate_state(result)
    return result


def record_preview_approval(state, *, reviewer, recorded_at, evidence_ref):
    """Bind explicit approval to the exact QA-passed preview artifact."""
    validate_state(state)
    _require_recording_status(
        state, "awaiting_preview_approval", "awaiting_preview_approval"
    )
    preview = _require_qa_passed_preview(state)
    video_id = state["providers"]["heygen"]["preview_video_id"]
    _reject_auto_reviewer(reviewer)
    _require_evidence_text(reviewer, "preview approval evidence")
    _require_approval_timestamp(recorded_at, label="preview approval")
    _require_opaque_reference(evidence_ref, "preview approval reference")
    expected = {
        "preview": True,
        "preview_reviewer": reviewer,
        "preview_artifact_sha256": preview["sha256"],
        "preview_video_id": video_id,
        "preview_recorded_at": recorded_at,
        "preview_evidence_ref": evidence_ref,
    }
    result = deepcopy(state)
    approval = result.setdefault("approval", {})
    for field, value in expected.items():
        if field == "preview" and approval.get(field) is False:
            approval[field] = value
            continue
        _require_matching_or_absent(approval, field, value, "preview approval")
        approval[field] = value
    validate_state(result)
    return result


def record_raw_video(
    state,
    *,
    video_id,
    content_sha256,
    artifact_ref,
    qa_passed,
):
    """Record one full HeyGen raw render and its local QA result."""
    validate_state(state)
    _require_recording_status(state, "full_raw_rendering", "raw_qa")
    _require_provider_id(video_id, "HeyGen video ID")
    _require_sha256(content_sha256, "raw artifact evidence")
    if type(qa_passed) is not bool:
        raise ValueError("raw artifact QA result must be a boolean")
    _require_stable_reference(
        artifact_ref, "raw artifact reference", allow_local_file=True
    )
    result = deepcopy(state)
    heygen = result.setdefault("providers", {}).setdefault("heygen", {})
    _require_matching_or_absent(heygen, "video_id", video_id, "video ID")
    heygen["video_id"] = video_id
    raw_video = {
        "kind": "full_raw",
        "sha256": content_sha256,
        "qa_passed": qa_passed,
        "ref": artifact_ref,
    }
    artifacts = result.setdefault("artifacts", {})
    _require_matching_or_absent(
        artifacts, "raw_video", raw_video, "raw video artifact"
    )
    artifacts["raw_video"] = raw_video
    result["status"] = "raw_qa"
    validate_state(result)
    return result


def record_raw_approval(state, *, reviewer, recorded_at, evidence_ref):
    """Bind explicit approval to the exact QA-passed full raw artifact."""
    validate_state(state)
    _require_recording_status(
        state, "awaiting_raw_approval", "awaiting_raw_approval"
    )
    _require_qa_passed_raw(state)
    if reviewer == AUTO_REVIEWER:
        _require_auto_job_route(state)
    raw_video = state["artifacts"]["raw_video"]
    video_id = state["providers"]["heygen"]["video_id"]
    expected = {
        "raw": True,
        "reviewer": reviewer,
        "raw_artifact_sha256": raw_video["sha256"],
        "heygen_video_id": video_id,
        "recorded_at": recorded_at,
        "evidence_ref": evidence_ref,
    }
    result = deepcopy(state)
    approval = result.setdefault("approval", {})
    for field, value in expected.items():
        if field == "raw" and approval.get(field) is False:
            approval[field] = value
            continue
        _require_matching_or_absent(approval, field, value, "raw approval")
        approval[field] = value
    validate_state(result)
    return result


def record_auto_raw_approval(state, *, recorded_at, evidence_ref):
    """Bind QA-passed full-raw approval for an auto-mode job."""
    validate_state(state)
    _require_auto_job_route(state)
    if state["status"] == "raw_qa":
        state = transition(state, "awaiting_raw_approval")
    return record_raw_approval(
        state,
        reviewer=AUTO_REVIEWER,
        recorded_at=recorded_at,
        evidence_ref=evidence_ref,
    )


def migrate_v1(old, *, source_bytes=None, legacy_preservation="caller-managed"):
    """Map safe v1 fields to v3 and retain unknown legacy data externally."""
    if not isinstance(old, dict):
        raise ValueError("legacy state must be a JSON object")
    _require_standard_json(old, "legacy state")
    try:
        canonical = json.dumps(
            old,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("legacy state must contain only standard JSON values") from error

    if "version" in old:
        version = old["version"]
        if type(version) is int and version == 3:
            migrated = deepcopy(old)
            validate_state(migrated)
            return migrated
        if type(version) is int and version == 2:
            return migrate_v2(
                old,
                source_bytes=source_bytes,
                legacy_preservation=legacy_preservation,
            )
        if type(version) is not int or version != 1:
            raise ValueError("unsupported state version")

    if source_bytes is not None and type(source_bytes) is not bytes:
        raise ValueError("source bytes must be bytes")
    if legacy_preservation not in _PRESERVATION_STRATEGIES:
        raise ValueError("unsupported legacy preservation strategy")

    status = old.get("status", "created")
    legacy_status_map = {
        "created": "created",
        "planned": "planned",
        "preview_choice_recorded": "planned",
        "audio_ready": "planned",
        "image_ready": "planned",
        "raw_rendering": "planned",
        "raw_qa": "planned",
        "awaiting_raw_approval": "planned",
        "post_production": "planned",
        "final_qa": "planned",
        "complete": "planned",
    }
    if not isinstance(status, str) or status not in legacy_status_map:
        raise ValueError("unknown legacy state status")
    status = legacy_status_map[status]

    approval = old.get("approval", {})
    if not isinstance(approval, dict):
        raise ValueError("approval must be a JSON object")
    raw_approval = approval.get("raw", False)
    if "raw_approved" in old:
        legacy_raw = old["raw_approved"]
        if type(legacy_raw) is not bool:
            raise ValueError("raw approval must be a boolean")
        if "raw" in approval and approval["raw"] is not legacy_raw:
            raise ValueError("conflicting raw approval values")
        raw_approval = legacy_raw
    if type(raw_approval) is not bool:
        raise ValueError("raw approval must be a boolean")

    # Legacy approval was not bound to a QA-passed full-raw fingerprint. Never
    # inherit it as authority for post-production; require explicit re-approval.
    raw_approval = False
    legacy_heygen = _legacy_provider(old, "heygen")
    providers = {}
    assets = {}

    preview_video_id = legacy_heygen.get("preview_video_id")
    if preview_video_id is not None:
        _require_heygen_preview_id(preview_video_id)
        providers["heygen"] = {"preview_video_id": preview_video_id}

    fingerprint_contents = canonical if source_bytes is None else source_bytes
    fingerprint_basis = "canonical-json" if source_bytes is None else "exact-source-bytes"
    migrated = {
        "version": 3,
        "status": status,
        "approval": {"image": False, "preview": False, "raw": raw_approval},
        "providers": providers,
        "assets": assets,
        "migration": {
            "source_version": 1,
            "source_sha256": hashlib.sha256(fingerprint_contents).hexdigest(),
            "fingerprint_basis": fingerprint_basis,
            "unmapped_field_count": _count_unmapped_fields(old),
            "legacy_preservation": legacy_preservation,
            "legacy_embedded": False,
        },
    }
    validate_state(migrated)
    return migrated


def migrate_v2(old, *, source_bytes=None, legacy_preservation="caller-managed"):
    """Conservatively migrate a strict v2 state to the v3 approval workflow."""
    if not isinstance(old, dict):
        raise ValueError("v2 state must be a JSON object")
    _require_standard_json(old, "v2 state")
    canonical = json.dumps(
        old,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if old.get("version") != 2 or type(old.get("version")) is not int:
        raise ValueError("state version must be 2")
    allowed_fields = {
        "version",
        "status",
        "approval",
        "providers",
        "assets",
        "artifacts",
        "error",
        "retry",
        "migration",
    }
    if set(old) - allowed_fields:
        raise ValueError("unsupported state field")
    old_statuses = {
        "created",
        "planned",
        "preview_choice_recorded",
        "assets_ready",
        "audio_ready",
        "raw_rendering",
        "raw_qa",
        "awaiting_raw_approval",
        "post_production",
        "final_qa",
        "complete",
    }
    status = old.get("status")
    if status not in old_statuses:
        raise ValueError("unknown v2 state status")

    providers = deepcopy(old.get("providers", {}))
    assets = deepcopy(old.get("assets", {}))
    artifacts = deepcopy(old.get("artifacts", {}))
    for value, label in (
        (providers, "providers"),
        (assets, "assets"),
        (artifacts, "artifacts"),
    ):
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object")
    _validate_v2_providers(providers)
    _validate_v2_assets(assets)
    _validate_v2_artifacts(artifacts)

    old_approval = old.get("approval", {"raw": False})
    if not isinstance(old_approval, dict):
        raise ValueError("approval must be a JSON object")
    raw_approved = old_approval.get("raw", False)
    if type(raw_approved) is not bool:
        raise ValueError("raw approval must be a boolean")
    if raw_approved:
        required = {
            "raw",
            "reviewer",
            "raw_artifact_sha256",
            "heygen_video_id",
            "recorded_at",
            "evidence_ref",
        }
        if set(old_approval) != required:
            raise ValueError("raw approval evidence is incomplete")
        approval = {
            "image": False,
            "preview": False,
            **deepcopy(old_approval),
        }
    else:
        if set(old_approval) != {"raw"}:
            raise ValueError("unsupported v2 approval field")
        approval = {"image": False, "preview": False, "raw": False}

    if source_bytes is not None and type(source_bytes) is not bytes:
        raise ValueError("source bytes must be bytes")
    if legacy_preservation not in _PRESERVATION_STRATEGIES:
        raise ValueError("unsupported legacy preservation strategy")
    fingerprint_contents = canonical if source_bytes is None else source_bytes
    fingerprint_basis = "canonical-json" if source_bytes is None else "exact-source-bytes"
    migrated = {
        "version": 3,
        "status": "created" if status == "created" else "planned",
        "approval": approval,
        "providers": providers,
        "assets": assets,
        "artifacts": artifacts,
        "error": {},
        "retry": {},
        "migration": {
            "source_version": 2,
            "source_sha256": hashlib.sha256(fingerprint_contents).hexdigest(),
            "fingerprint_basis": fingerprint_basis,
            "unmapped_field_count": 0,
            "legacy_preservation": legacy_preservation,
            "legacy_embedded": False,
        },
    }
    validate_state(migrated)
    return migrated


def _legacy_provider(old, name):
    value = old.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _count_unmapped_fields(old) -> int:
    mapped_paths = {
        ("version",),
        ("status",),
        ("raw_approved",),
        ("approval", "raw"),
        ("heygen", "preview_video_id"),
    }

    def count_nested(value, path):
        if type(value) is dict:
            return sum(count_field(nested, path + (key,)) for key, nested in value.items())
        if type(value) is list:
            return sum(count_nested(nested, path) for nested in value)
        return 0

    def count_field(value, path):
        mapped = path in mapped_paths
        mapped_container = any(mapped_path[: len(path)] == path for mapped_path in mapped_paths)
        return (0 if mapped or mapped_container else 1) + count_nested(value, path)

    return sum(count_field(value, (key,)) for key, value in old.items())


def _require_recording_status(state, predecessor, result_status) -> None:
    if state["status"] not in {predecessor, result_status}:
        raise ValueError(
            f"event requires {predecessor} or {result_status} status"
        )


def _reject_auto_reviewer(reviewer) -> None:
    if reviewer == AUTO_REVIEWER:
        raise ValueError("auto-mode reviewer is only valid for auto raw approval")


def _require_auto_job_route(state) -> None:
    assets = state.get("assets")
    route = assets.get("job_route") if isinstance(assets, dict) else None
    if not isinstance(route, dict) or route.get("operating_mode") != "auto":
        raise ValueError("auto raw approval requires operating_mode=auto")
    _validate_assets({"job_route": route})
    if route != AUTO_JOB_ROUTE:
        raise ValueError("conflicting job route")


def _require_matching_auto_defaults(state) -> None:
    _require_auto_job_route(state)
    expected_image = {
        "identity_master_alias": "image1",
        "generate_new": False,
        "source": "original_image1",
    }
    if _require_job_image(state) != expected_image:
        raise ValueError("conflicting auto image selection")
    if _preview_requested(state) is not False:
        raise ValueError("auto mode requires preview_requested=False")


def _require_matching_or_absent(container, field, expected, label) -> None:
    if field in container and container[field] != expected:
        raise ValueError(f"conflicting {label}")


def _require_job_image(state):
    assets = state.get("assets")
    job_image = assets.get("job_image") if isinstance(assets, dict) else None
    if not isinstance(job_image, dict):
        raise ValueError("job image choice is required")
    _validate_assets({"job_image": job_image})
    return job_image


def _require_sha256(value, label) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} SHA-256 is invalid")


def _preview_requested(state):
    providers = state.get("providers")
    heygen = providers.get("heygen") if isinstance(providers, dict) else None
    if not isinstance(heygen, dict) or type(heygen.get("preview_requested")) is not bool:
        raise ValueError("preview choice is required")
    return heygen["preview_requested"]


def _require_real_render_evidence(evidence) -> None:
    if not isinstance(evidence, dict) or set(evidence) != _RENDER_EVIDENCE_FIELDS:
        raise ValueError("real render evidence is incomplete")
    progress = evidence["progress"]
    video_count = evidence["video_count"]
    real = (
        evidence["session_status"]
        in {"generating", "rendering", "processing", "completed"}
        and type(progress) in {int, float}
        and math.isfinite(progress)
        and progress > 0
        and type(video_count) is int
        and video_count > 0
        and evidence["generate_button_visible"] is False
        and evidence["avatar_bound"] is True
        and evidence["resource_type"] == "video"
    )
    if not real:
        raise ValueError("real render evidence is required")


def _require_recorded_render_start(state, kind) -> None:
    artifact_field = f"{kind}_render_start"
    artifacts = state.get("artifacts")
    render_start = artifacts.get(artifact_field) if isinstance(artifacts, dict) else None
    if not isinstance(render_start, dict):
        raise ValueError("real render evidence is required")
    _validate_artifacts({artifact_field: render_start})


def _require_qa_passed_preview(state):
    artifacts = state.get("artifacts")
    preview = artifacts.get("preview_video") if isinstance(artifacts, dict) else None
    if not isinstance(preview, dict):
        raise ValueError("preview artifact must pass QA before approval")
    _validate_artifacts({"preview_video": preview})
    if preview["qa_passed"] is not True:
        raise ValueError("preview artifact must pass QA before approval")
    providers = state.get("providers")
    heygen = providers.get("heygen") if isinstance(providers, dict) else None
    if not isinstance(heygen, dict) or "preview_video_id" not in heygen:
        raise ValueError("preview artifact must have a HeyGen video ID before approval")
    _require_provider_id(heygen["preview_video_id"], "HeyGen preview video ID")
    return preview


def _require_qa_passed_raw(state) -> None:
    artifacts = state.get("artifacts")
    raw_video = artifacts.get("raw_video") if isinstance(artifacts, dict) else None
    if not isinstance(raw_video, dict):
        raise ValueError("raw artifact must pass QA before approval")
    _validate_artifacts({"raw_video": raw_video})
    if raw_video["qa_passed"] is not True:
        raise ValueError("raw artifact must pass QA before approval")
    providers = state.get("providers")
    heygen = providers.get("heygen") if isinstance(providers, dict) else None
    if not isinstance(heygen, dict) or "video_id" not in heygen:
        raise ValueError("raw artifact must have a HeyGen video ID before approval")
    _require_provider_id(heygen["video_id"], "HeyGen video ID")


def _validate_providers(providers) -> None:
    for provider, details in providers.items():
        if provider != "heygen" or not isinstance(details, dict):
            raise ValueError("provider details must be a JSON object")
        allowed = {
            "preview_requested",
            "preview_video_id",
            "audio_id",
            "video_id",
        }
        if set(details) - allowed:
            raise ValueError("unsupported provider field")
        for field, value in details.items():
            if field == "preview_requested":
                if type(value) is not bool:
                    raise ValueError("preview choice must be a boolean")
            elif field == "preview_video_id":
                _require_heygen_preview_id(value)
            else:
                _require_provider_id(value, "provider ID")


def _validate_v2_providers(providers) -> None:
    if set(providers) - {"heygen"}:
        raise ValueError("unsupported v2 provider")
    if not providers:
        return
    details = providers["heygen"]
    if not isinstance(details, dict) or set(details) - {
        "preview_video_id",
        "audio_id",
        "video_id",
    }:
        raise ValueError("unsupported v2 provider field")
    _validate_providers(providers)


def _validate_assets(assets) -> None:
    allowed = {
        "voice": {"voice_id", "alias"},
        "identity": {"avatar_group_id", "avatar_look_id", "alias"},
        "job_image": {"identity_master_alias", "generate_new", "source"},
        "job_route": {"operating_mode", "voice_provider", "material_route"},
    }
    for asset_type, details in assets.items():
        if asset_type not in allowed or not isinstance(details, dict):
            raise ValueError("unsupported asset field")
        if set(details) != allowed[asset_type]:
            raise ValueError("unsupported asset field")
        if asset_type == "job_image":
            _require_provider_id(
                details["identity_master_alias"], "identity master alias"
            )
            if type(details["generate_new"]) is not bool:
                raise ValueError("image generation choice must be a boolean")
            if details["source"] not in {
                "pending",
                "original_image1",
                "generated_candidate",
            }:
                raise ValueError("unsupported job image source")
            continue
        if asset_type == "job_route":
            if details["operating_mode"] not in {"interactive", "auto"}:
                raise ValueError("operating_mode must be interactive or auto")
            if details["voice_provider"] not in {"minimax", "heygen"}:
                raise ValueError("voice_provider must be minimax or heygen")
            if details["material_route"] not in {"none", "company"}:
                raise ValueError("material_route must be none or company")
            continue
        for field, value in details.items():
            _require_provider_id(value, "asset ID")


def _validate_v2_assets(assets) -> None:
    if set(assets) - {"voice", "identity"}:
        raise ValueError("unsupported v2 asset field")
    _validate_assets(assets)


def _validate_artifacts(artifacts) -> None:
    if set(artifacts) - {
        "audio",
        "image_candidate",
        "preview_render_start",
        "full_raw_render_start",
        "preview_video",
        "raw_video",
    }:
        raise ValueError("unsupported artifact field")
    candidate = artifacts.get("image_candidate")
    if candidate is not None:
        if (
            not isinstance(candidate, dict)
            or set(candidate) != _IMAGE_CANDIDATE_FIELDS
        ):
            raise ValueError("candidate image evidence is invalid")
        _require_sha256(candidate["sha256"], "candidate image")
        _require_stable_reference(
            candidate["ref"], "candidate image reference", allow_local_file=True
        )
    audio = artifacts.get("audio")
    if audio is not None:
        if not isinstance(audio, dict) or set(audio) != _AUDIO_ARTIFACT_FIELDS:
            raise ValueError("audio artifact evidence is invalid")
        _require_sha256(audio["sha256"], "audio artifact")
        duration = audio["duration_seconds"]
        if (
            type(duration) not in {int, float}
            or not math.isfinite(duration)
            or duration <= 0
        ):
            raise ValueError("audio artifact evidence is invalid")
    for kind in ("preview", "full_raw"):
        render_start = artifacts.get(f"{kind}_render_start")
        if render_start is None:
            continue
        if (
            not isinstance(render_start, dict)
            or set(render_start) != _RENDER_START_FIELDS
        ):
            raise ValueError("render start evidence is invalid")
        _require_provider_id(render_start["video_id"], "render video ID")
        _require_real_render_evidence(render_start["evidence"])
    preview_video = artifacts.get("preview_video")
    if preview_video is not None:
        if (
            not isinstance(preview_video, dict)
            or set(preview_video) != _VIDEO_ARTIFACT_FIELDS
            or preview_video["kind"] != "preview"
        ):
            raise ValueError("preview artifact evidence is invalid")
        _require_sha256(preview_video["sha256"], "preview artifact evidence")
        if type(preview_video["qa_passed"]) is not bool:
            raise ValueError("preview artifact evidence is invalid")
        _require_stable_reference(
            preview_video["ref"],
            "preview artifact reference",
            allow_local_file=True,
        )
    raw_video = artifacts.get("raw_video")
    if raw_video is None:
        return
    if not isinstance(raw_video, dict) or set(raw_video) != _RAW_ARTIFACT_FIELDS:
        raise ValueError("raw artifact evidence is invalid")
    if raw_video["kind"] != "full_raw":
        raise ValueError("raw artifact evidence is invalid")
    _require_sha256(raw_video["sha256"], "raw artifact evidence")
    if type(raw_video["qa_passed"]) is not bool:
        raise ValueError("raw artifact evidence is invalid")
    _require_stable_reference(
        raw_video["ref"], "raw artifact reference", allow_local_file=True
    )


def _validate_v2_artifacts(artifacts) -> None:
    if set(artifacts) - {"audio", "raw_video"}:
        raise ValueError("unsupported v2 artifact field")
    _validate_artifacts(artifacts)


def _require_bound_raw_approval(state) -> None:
    approval = state.get("approval")
    if not isinstance(approval, dict) or approval.get("raw") is not True:
        raise ValueError("raw approval evidence is required before post_production")
    required = {
        "reviewer",
        "raw_artifact_sha256",
        "heygen_video_id",
        "recorded_at",
        "evidence_ref",
    }
    if not required.issubset(approval):
        raise ValueError("raw approval evidence is incomplete")
    _require_evidence_text(approval["reviewer"], "raw approval evidence")
    _require_approval_timestamp(approval["recorded_at"])
    _require_opaque_reference(approval["evidence_ref"], "raw approval reference")
    approved_sha256 = approval["raw_artifact_sha256"]
    if not isinstance(approved_sha256, str) or not _SHA256.fullmatch(approved_sha256):
        raise ValueError("raw approval evidence is invalid")
    approved_video_id = approval["heygen_video_id"]
    _require_provider_id(approved_video_id, "raw approval evidence")

    artifacts = state.get("artifacts")
    raw_video = artifacts.get("raw_video") if isinstance(artifacts, dict) else None
    if not isinstance(raw_video, dict):
        raise ValueError("raw artifact evidence is required before post_production")
    _validate_artifacts({"raw_video": raw_video})
    if raw_video["qa_passed"] is not True:
        raise ValueError("raw artifact must pass QA before post_production")
    if approved_sha256 != raw_video["sha256"]:
        raise ValueError("raw approval evidence does not match raw artifact evidence")

    providers = state.get("providers")
    heygen = providers.get("heygen") if isinstance(providers, dict) else None
    if not isinstance(heygen, dict) or "video_id" not in heygen:
        raise ValueError("raw artifact evidence is incomplete")
    _require_provider_id(heygen["video_id"], "raw artifact evidence")
    if approved_video_id != heygen["video_id"]:
        raise ValueError("raw approval evidence does not match raw artifact evidence")


def _require_bound_image_approval(state) -> None:
    approval = state.get("approval")
    required = {
        "image_reviewer",
        "image_candidate_sha256",
        "image_artifact_ref",
        "image_recorded_at",
        "image_evidence_ref",
    }
    if not isinstance(approval, dict) or not required.issubset(approval):
        raise ValueError("image approval evidence is incomplete")
    _require_evidence_text(approval["image_reviewer"], "image approval evidence")
    _require_approval_timestamp(
        approval["image_recorded_at"], label="image approval"
    )
    _require_opaque_reference(
        approval["image_evidence_ref"], "image approval reference"
    )
    _require_sha256(
        approval["image_candidate_sha256"], "image approval evidence"
    )
    _require_stable_reference(
        approval["image_artifact_ref"],
        "image approval artifact reference",
        allow_local_file=True,
    )
    artifacts = state.get("artifacts")
    candidate = (
        artifacts.get("image_candidate") if isinstance(artifacts, dict) else None
    )
    if not isinstance(candidate, dict):
        raise ValueError("candidate image evidence is required")
    _validate_artifacts({"image_candidate": candidate})
    if (
        approval["image_candidate_sha256"] != candidate["sha256"]
        or approval["image_artifact_ref"] != candidate["ref"]
    ):
        raise ValueError("image approval evidence does not match candidate image")


def _require_bound_preview_approval(state) -> None:
    approval = state.get("approval")
    required = {
        "preview_reviewer",
        "preview_artifact_sha256",
        "preview_video_id",
        "preview_recorded_at",
        "preview_evidence_ref",
    }
    if (
        not isinstance(approval, dict)
        or approval.get("preview") is not True
        or not required.issubset(approval)
    ):
        raise ValueError("preview approval evidence is incomplete")
    _require_evidence_text(
        approval["preview_reviewer"], "preview approval evidence"
    )
    _require_approval_timestamp(
        approval["preview_recorded_at"], label="preview approval"
    )
    _require_opaque_reference(
        approval["preview_evidence_ref"], "preview approval reference"
    )
    _require_sha256(
        approval["preview_artifact_sha256"], "preview approval evidence"
    )
    _require_provider_id(
        approval["preview_video_id"], "preview approval video ID"
    )
    preview = _require_qa_passed_preview(state)
    video_id = state["providers"]["heygen"]["preview_video_id"]
    if (
        approval["preview_artifact_sha256"] != preview["sha256"]
        or approval["preview_video_id"] != video_id
    ):
        raise ValueError("preview approval evidence does not match preview artifact")


def _require_evidence_text(value, label) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is invalid")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError(f"{label} is invalid")


def _require_approval_timestamp(value, *, label="raw approval") -> None:
    if (
        not isinstance(value, str)
        or not _RFC3339_TIMESTAMP.fullmatch(value)
        or value.endswith("-00:00")
    ):
        raise ValueError(f"{label} timestamp is invalid")
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(f"{label} timestamp is invalid") from error
    if parsed.utcoffset() is None:
        raise ValueError(f"{label} timestamp is invalid")


def _require_stable_reference(value, label, *, allow_local_file=False) -> None:
    _require_evidence_text(value, label)
    is_local_file_reference = (
        allow_local_file and _LOCAL_FILE_REFERENCE.search(value) is not None
    )
    if (
        value != value.strip()
        or value.startswith(("//", "\\\\"))
        or "://" in value
        or (
            _URI_SCHEME.match(value)
            and not _WINDOWS_ABSOLUTE_PATH.match(value)
        )
        or any(character in "?#" for character in value)
        or _SENSITIVE_REFERENCE.search(value)
        or (
            not is_local_file_reference
            and _CREDENTIAL_SCHEME_REFERENCE.search(value)
        )
        or _JWT_REFERENCE.search(value)
        or _SECRET_PREFIX_REFERENCE.search(value)
    ):
        raise ValueError(f"{label} is invalid")


def _require_opaque_reference(value, label) -> None:
    _require_stable_reference(value, label)
    if any(character in "/\\" for character in value):
        raise ValueError(f"{label} is invalid")


def _validate_migration(migration) -> None:
    required = {
        "source_version",
        "source_sha256",
        "fingerprint_basis",
        "unmapped_field_count",
        "legacy_preservation",
        "legacy_embedded",
    }
    if set(migration) != required:
        raise ValueError("invalid migration provenance")
    if (
        type(migration["source_version"]) is not int
        or migration["source_version"] not in {1, 2}
    ):
        raise ValueError("invalid migration provenance")
    if not isinstance(migration["source_sha256"], str) or not _SHA256.fullmatch(
        migration["source_sha256"]
    ):
        raise ValueError("invalid migration provenance")
    if migration["fingerprint_basis"] not in _MIGRATION_BASES:
        raise ValueError("invalid migration provenance")
    count = migration["unmapped_field_count"]
    if type(count) is not int or count < 0:
        raise ValueError("invalid migration provenance")
    if migration["legacy_preservation"] not in _PRESERVATION_STRATEGIES:
        raise ValueError("invalid migration provenance")
    if migration["legacy_embedded"] is not False:
        raise ValueError("invalid migration provenance")


def _require_provider_id(value, label) -> None:
    if not isinstance(value, str) or not _PROVIDER_ID.fullmatch(value):
        raise ValueError(f"{label} must be a provider ID")


def _require_heygen_preview_id(value) -> None:
    label = "heygen preview provider ID"
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty opaque ID")
    if value != value.strip() or any(
        character.isspace() or unicodedata.category(character) == "Cc"
        for character in value
    ):
        raise ValueError(f"{label} must not contain whitespace or control characters")
    if (
        value.startswith("//")
        or _URI_SCHEME.match(value)
        or any(character in "/\\?#" for character in value)
    ):
        raise ValueError(f"{label} must be an opaque ID, not a URL or path")


def _require_standard_json(value, label: str, active=None) -> None:
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return
    if value_type is float:
        if math.isfinite(value):
            return
        raise ValueError(f"{label} must contain only standard JSON values")
    if value_type not in {dict, list}:
        raise ValueError(f"{label} must contain only standard JSON values")

    if active is None:
        active = set()
    container_id = id(value)
    if container_id in active:
        raise ValueError(f"{label} must contain only standard JSON values")
    active.add(container_id)
    try:
        if value_type is dict:
            for key, nested in value.items():
                if type(key) is not str:
                    raise ValueError(f"{label} must contain only standard JSON values")
                _require_standard_json(nested, label, active)
        else:
            for nested in value:
                _require_standard_json(nested, label, active)
    finally:
        active.remove(container_id)
