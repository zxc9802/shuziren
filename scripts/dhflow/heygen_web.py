"""Deterministic plans for structured HeyGen plugin submissions."""

import hashlib
import json
import math
import re
from copy import deepcopy

from scripts.dhflow.performance_director import (
    PERFORMANCE_PRIMITIVE_LIBRARY_ID,
    PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE,
    PERFORMANCE_REFERENCE_ID,
    PERFORMANCE_REFERENCE_SHA256,
    load_performance_primitive_library,
    primitive_prompt_fragments,
)


HEYGEN_WEB_TRANSPORT = "heygen-plugin-structured"

_OPAQUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}\Z")
_ACTION_ORDER = (
    "verifyPerformanceReference",
    "inspectConnectedHeyGenAccount",
    "resolveOrUploadApprovedLook",
    "resolveExactVoice",
    "buildPerformanceBeatMap",
    "buildStructuredPluginPayload",
    "verifyBeforeSpend",
    "submitPluginVideo",
    "verifyRealRender",
    "pollExistingVideo",
)


def build_web_submission_plan(
    *,
    script,
    voice_plan,
    visual_plan,
    performance_plan,
    voice_id,
    avatar_group_id,
):
    """Build a strict structured-plugin plan for the connected HeyGen account."""
    _require_nonempty_text(script, "script")
    _require_standard_json(voice_plan, "voice_plan")
    _require_standard_json(visual_plan, "visual_plan")
    _require_standard_json(performance_plan, "performance_plan")
    _require_opaque_id(voice_id, "voice_id")
    _require_opaque_id(avatar_group_id, "avatar_group_id")
    voice_segments = _require_sequence(voice_plan, "segments", "voice_plan")
    performance_beats = _require_sequence(
        performance_plan, "beats", "performance_plan"
    )
    performance_reference, primitive_library = _require_performance_system(
        performance_plan
    )
    _require_exact_script(script, voice_segments, "voice_plan")
    _require_exact_script(script, performance_beats, "performance_plan")
    _require_matching_beats(voice_segments, performance_beats)
    _validate_visual_plan(visual_plan)
    if performance_plan.get("hand_topology") != visual_plan["hand_topology"]:
        raise ValueError("performance and visual hand topology must match")
    if performance_plan.get("view_mode") != visual_plan["view_mode"]:
        raise ValueError("performance and visual view mode must match")

    motion_prompt = _build_motion_prompt(performance_beats, visual_plan)
    delivery_prompt = _build_delivery_prompt(voice_segments)
    script_sha256 = hashlib.sha256(script.encode("utf-8")).hexdigest()
    pre_submit = {
        "requiredAvatarGroupId": avatar_group_id,
        "requiredVoiceId": voice_id,
        "identityMasterAlias": visual_plan["identity_master_alias"],
        "approvedLookSource": "approved_job_image_or_original_image1",
        "maxCandidateImages": 1,
        "viewMode": visual_plan["view_mode"],
        "subjectOrientation": deepcopy(visual_plan["subject_orientation"]),
        "exactScript": script,
        "exactScriptSha256": script_sha256,
        "deliveryPlan": deepcopy(voice_segments),
        "deliveryPrompt": delivery_prompt,
        "aspectRatio": "9:16",
        "resolution": "720p",
        "requiredAvatarCapability": "avatar_iv",
        "engineSelection": "plugin_auto_from_avatar_type",
        "captionsEnabled": False,
        "musicEnabled": False,
        "bRollEnabled": False,
        "cameraMotionEnabled": False,
        "motionPrompt": motion_prompt,
        "performanceReference": performance_reference,
        "performancePrimitiveLibrary": primitive_library,
        "performanceBeatMapContract": {
            "artifact": "performance-beat-map.json",
            "timingScope": "planning_and_rendered_qa_only",
            "providerFrameAccurateTimingClaimed": False,
            "exactReferenceTimelineCopyForbidden": True,
            "requiredBeforeSubmitWhen": "voice_provider=minimax|indextts",
            "requiredAfterRenderWhen": "voice_provider=heygen",
            "mustBindExactAudioSha256": True,
        },
        "previewContract": {
            "targetSeconds": 15,
            "useApprovedOpeningExcerpt": True,
            "verifyActualDuration": True,
            "claimExactOnlyAfterMeasurement": True,
        },
        "durationVerification": {
            "basis": "exact_script_with_bound_voice",
            "requiredScriptSha256": script_sha256,
            "requireCompleteScriptCoverage": True,
            "rejectTruncation": True,
            "rejectUnexpectedSilence": True,
        },
        "guards": {
            "avatarMustBeBound": True,
            "avatarMustSupportAvatarIV": True,
            "voiceIdMustMatch": True,
            "scriptMustMatchByteForByte": True,
            "structuredPluginToolRequired": True,
            "videoAgentRewriteForbidden": True,
            "durationMustMatchCompleteScript": True,
            "motionPromptMustBePresent": True,
            "motionPromptMustDescribeLivingIdle": True,
            "performanceReferenceMustBeVerified": True,
            "performancePrimitiveLibraryMustBeVerified": True,
            "minimaxAudioPerformanceBeatMapRequired": True,
            "extrasMustBeDisabled": True,
            "cameraMustRemainLocked": True,
            "settingsMustMatch": True,
            "candidateCountMustNotExceedOne": True,
            "viewModeMustMatchApprovedLook": True,
            "onFailure": "stop_before_spend",
        },
    }
    plan = {
        "transport": HEYGEN_WEB_TRANSPORT,
        "creditSource": "connected_heygen_subscription_credits",
        "actionOrder": list(_ACTION_ORDER),
        "preSubmit": pre_submit,
        "actions": {
            "verifyPerformanceReference": {
                "tool": "python3 scripts/verify_performance_reference.py --json",
                "requiredReferenceId": PERFORMANCE_REFERENCE_ID,
                "requiredSha256": PERFORMANCE_REFERENCE_SHA256,
                "localOnly": True,
                "providerUploadForbidden": True,
            },
            "inspectConnectedHeyGenAccount": {
                "tool": "get_current_user",
                "requireConnectedAccount": True,
                "requireSubscriptionCredits": True,
            },
            "resolveOrUploadApprovedLook": {
                "requiredAvatarGroupId": avatar_group_id,
                "allowedSources": ["original_image1", "approved_generated_candidate"],
                "requiresExactApprovedArtifact": True,
                "lookDiscoveryTool": "list_avatar_looks",
                "assetUploadBridge": {
                    "allowed": True,
                    "transport": "heygen-v3-assets-only",
                    "onlyForApprovedLocalArtifact": True,
                },
            },
            "resolveExactVoice": {
                "requiredVoiceId": voice_id,
                "requiresCompletedPrivateClone": True,
                "verificationTool": "get_voice",
            },
            "buildPerformanceBeatMap": {
                "tool": "python3 scripts/build_performance_beat_map.py --voice-plan <voice-plan.json> --performance-plan <performance-plan.json> --timings <final-audio-segments.json> --audio <exact-final-audio> --out <performance-beat-map.json>",
                "requiredBeforeSubmitWhen": "voice_provider=minimax|indextts",
                "requiredAfterRenderWhen": "voice_provider=heygen",
                "timingScope": "planning_and_rendered_qa_only",
                "providerFrameAccurateTimingClaimed": False,
                "mustBindExactAudioSha256": True,
            },
            "buildStructuredPluginPayload": {
                "script": script,
                "scriptSha256": script_sha256,
                "voiceId": voice_id,
                "aspectRatio": "9:16",
                "resolution": "720p",
                "caption": False,
                "motionPrompt": motion_prompt,
                "rewriteAllowed": False,
            },
            "verifyBeforeSpend": deepcopy(pre_submit["guards"]),
            "submitPluginVideo": {
                "allowedTools": [
                    "create_video_from_avatar",
                    "create_video_from_image",
                ],
                "videoAgentAllowedForExactScript": False,
                "submitCount": 1,
                "requiresAllPreSubmitGuards": True,
            },
            "verifyRealRender": {
                "requiresStableVideoId": True,
                "requiresBoundAvatar": True,
                "requiresVideoResource": True,
                "rejectMissingOrZeroProgressSession": True,
                "rejectSuccessTextWithoutResource": True,
            },
            "pollExistingVideo": {
                "reuseSubmittedVideoId": True,
                "repeatGenerateOnSlowProgress": False,
                "until": "completed_or_failed",
            },
        },
    }
    _ensure_strict_json(plan)
    return plan


def classify_render_evidence(
    *,
    session_status,
    progress,
    video_count,
    generate_button_visible,
    avatar_bound,
    resource_type,
):
    """Classify observable UI state without trusting success-message text."""
    if not isinstance(session_status, str) or not isinstance(resource_type, str):
        return "blocked"
    if (
        type(progress) not in {int, float}
        or not math.isfinite(progress)
        or type(video_count) is not int
        or type(generate_button_visible) is not bool
        or type(avatar_bound) is not bool
    ):
        return "blocked"
    status = session_status.strip().lower()
    resource = resource_type.strip().lower()
    if resource in {"blueprint", "draft"} or (
        status == "thinking" and progress == 0 and video_count == 0
    ):
        return "blueprint_ready"
    real_video = (
        progress > 0
        and video_count > 0
        and generate_button_visible is False
        and avatar_bound is True
        and resource == "video"
    )
    if not real_video:
        return "blocked"
    if status in {"complete", "completed"} and progress >= 100:
        return "completed"
    if status in {"generating", "rendering", "processing"}:
        return "rendering"
    return "blocked"


def _require_sequence(plan, field, label):
    if not isinstance(plan, dict):
        raise ValueError(f"{label} must be a JSON object")
    sequence = plan.get(field)
    if not isinstance(sequence, list) or not sequence:
        raise ValueError(f"{label}.{field} must be a non-empty array")
    for item in sequence:
        if not isinstance(item, dict):
            raise ValueError(f"{label}.{field} must contain JSON objects")
    return sequence


def _require_exact_script(script, sequence, label):
    texts = []
    for item in sequence:
        text = item.get("text")
        if not isinstance(text, str):
            raise ValueError(f"{label} must contain exact script text")
        texts.append(text)
    if "".join(texts) != script:
        raise ValueError(f"{label} does not preserve the exact script")


def _require_matching_beats(voice_segments, performance_beats):
    voice = [(item.get("id"), item.get("text")) for item in voice_segments]
    performance = [(item.get("id"), item.get("text")) for item in performance_beats]
    if voice != performance:
        raise ValueError("voice and performance beats must match")


def _validate_visual_plan(visual_plan):
    if not isinstance(visual_plan, dict):
        raise ValueError("visual_plan must be a JSON object")
    required = {
        "identity_alias",
        "identity_master_alias",
        "hand_topology",
        "job_look",
        "camera",
        "aspect_ratio",
        "resolution",
        "view_mode",
        "subject_orientation",
    }
    if not required.issubset(visual_plan):
        raise ValueError("visual_plan is incomplete")
    if visual_plan["identity_alias"] != visual_plan["identity_master_alias"]:
        raise ValueError("identity master must match the selected identity")
    if visual_plan["camera"].get("locked") is not True:
        raise ValueError("camera must remain locked")
    if visual_plan["aspect_ratio"] != "9:16":
        raise ValueError("aspect ratio must be 9:16")
    if visual_plan["resolution"] != "720p":
        raise ValueError("resolution must be 720p")
    _validate_subject_orientation(
        visual_plan["view_mode"], visual_plan["subject_orientation"]
    )
    job_look = visual_plan["job_look"]
    if not isinstance(job_look, dict) or job_look.get("candidate_count") != 1:
        raise ValueError("exactly one candidate image is allowed")
    if job_look.get("explicit_approval_required") is not True:
        raise ValueError("candidate image requires explicit approval")


def _build_delivery_prompt(segments):
    directions = []
    for segment in segments:
        delivery = segment.get("delivery")
        if not isinstance(delivery, dict):
            raise ValueError("voice delivery plan is incomplete")
        directions.append(
            f"{segment.get('id')}: speed={delivery.get('speed')}, "
            f"emotion={delivery.get('emotion')}, emphasis={delivery.get('emphasis')}, "
            f"pause_before={delivery.get('pause_before')}, "
            f"pause_after={delivery.get('pause_after')}"
        )
    return "Vary pace and pauses by semantic beat; never use one constant speed. " + "; ".join(
        directions
    )


def _humanize_cue(token, fallback="natural"):
    if not isinstance(token, str) or not token.strip():
        return fallback
    return token.strip().replace("_", " ")


def _build_motion_prompt(beats, visual_plan):
    directions = []
    for beat in beats:
        face = beat.get("face", {})
        head = beat.get("head", {})
        hands = beat.get("hands", {})
        body = beat.get("body", {})
        primitive_prompt_fragments(beat.get("primitive_chain"))
        line = (
            f"{beat.get('id')} ({beat.get('role')}): the face leads with a "
            f"{_humanize_cue(face.get('intensity'), 'subtle')} "
            f"{_humanize_cue(face.get('action'))} cue; the head answers with a small "
            f"{_humanize_cue(head.get('action'))} that rides a slight neck-and-shoulder "
            "response, then settles back to the pose anchor"
        )
        if hands.get("enabled") and hands.get("main_action"):
            line += (
                f"; one compact unhurried {_humanize_cue(hands.get('main_action'))} "
                "gesture near the torso completes prepare, stroke, retract, and "
                "cooldown before the hands come to rest"
            )
        line += (
            f"; the body stays quietly alive with "
            f"{_humanize_cue(body.get('action'), 'steady breathing')}."
        )
        directions.append(line)
    view_mode = visual_plan["view_mode"]
    if view_mode == "front":
        gaze_direction = (
            "Front-facing neutral pose with direct eye contact and natural irregular blinks. "
            "All small head and gaze movements return to the front-facing anchor. "
        )
    else:
        frame_direction = (
            "frame left"
            if view_mode == "three_quarter_left_45"
            else "frame right"
        )
        gaze_direction = (
            "Maintain the approved 45-degree three-quarter side pose: torso and head stay "
            f"oriented toward {frame_direction}. Keep gaze on a natural off-camera conversation "
            "point in the same direction; never twist the eyes back toward the lens or alternate "
            "to direct eye contact. Natural irregular blinks and small head movements return to "
            "the same 45-degree pose and gaze anchor. "
        )
    living_idle = (
        "The subject is a real person mid-conversation, relaxed and engaged, never a "
        "statue. Quiet breathing stays visible as a gentle chest-and-shoulder rise and "
        "fall for the whole take. Between gestures the body holds a living idle: the "
        "head keeps a barely visible one-to-two-degree drift with small resettles, "
        "resting hands and fingers keep natural micro-relaxation, and blinks stay "
        "irregular with an occasional slightly longer reflective blink. Speech energy "
        "reaches the whole face: the jaw opens naturally on open vowels, cheeks and "
        "brows respond, and small head accents land on stressed syllables while phrase "
        "endings settle softly. Every head turn or nod rides on a slight neck-and-"
        "shoulder response absorbed by the torso, so the head never rotates on a frozen "
        "body. Channels stay staggered - face first, then head, then an optional hand "
        "stroke - and never peak together. A hand stroke never moves in isolation: the "
        "same phrase first changes the face, then produces a small head, neck, and shoulder "
        "response with a restrained torso counterweight. "
    )
    stability = (
        "Keep gestures compact, unhurried, and forearm-led near the torso. Keep facial "
        "geometry, eyewear, hairline, clothing, background, and framing locked and "
        "stable throughout motion. Avoid: fixed-period repetition, pendulum sway, "
        "continuous gesturing, camera motion, zoom, cuts, frozen statue idle, lip-only "
        "articulation on a static face, melting or warped hands, and identity drift."
    )
    return (
        "Fixed camera and fixed framing. "
        + gaze_direction
        + living_idle
        + " ".join(directions)
        + " "
        + stability
    )


def _require_performance_system(performance_plan):
    reference = performance_plan.get("reference")
    if type(reference) is not dict:
        raise ValueError("performance_plan.reference is required")
    expected = {
        "id": PERFORMANCE_REFERENCE_ID,
        "source_sha256": PERFORMANCE_REFERENCE_SHA256,
        "scope": "performance_only",
        "verification_required_before_spend": True,
        "provider_upload_forbidden": True,
    }
    for field, value in expected.items():
        if reference.get(field) != value or type(reference.get(field)) is not type(value):
            raise ValueError(f"performance_plan.reference.{field} is invalid")
    manifest = reference.get("manifest")
    if not isinstance(manifest, str) or not manifest.strip():
        raise ValueError("performance_plan.reference.manifest is required")

    contract = performance_plan.get("motion_contract")
    if type(contract) is not dict:
        raise ValueError("performance_plan.motion_contract is required")
    required_contract = (
        "whole_person_speaks",
        "hands_must_not_move_alone",
        "face_head_shoulders_torso_respond_to_speech",
        "channel_peaks_staggered",
        "repetitive_dead_silence_restarts_rejected",
    )
    for field in required_contract:
        if contract.get(field) is not True:
            raise ValueError(f"performance_plan.motion_contract.{field} must be true")

    primitive_library = performance_plan.get("primitive_library")
    if type(primitive_library) is not dict:
        raise ValueError("performance_plan.primitive_library is required")
    current_library, current_sha256 = load_performance_primitive_library()
    expected_library = {
        "id": PERFORMANCE_PRIMITIVE_LIBRARY_ID,
        "version": current_library["schema_version"],
        "source": PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE,
        "source_sha256": current_sha256,
        "provider_timing_contract": "semantic_relative_only",
        "frame_accurate_timing_claimed": False,
        "exact_reference_timeline_copy_forbidden": True,
    }
    for field, value in expected_library.items():
        if (
            primitive_library.get(field) != value
            or type(primitive_library.get(field)) is not type(value)
        ):
            raise ValueError(f"performance_plan.primitive_library.{field} is invalid")

    beats = performance_plan.get("beats")
    if not isinstance(beats, list) or not beats:
        raise ValueError("performance_plan.beats is required")
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise ValueError(f"performance_plan.beats[{index}] is invalid")
        chain = beat.get("primitive_chain")
        primitive_prompt_fragments(chain)
        hands = beat.get("hands")
        if not isinstance(hands, dict):
            raise ValueError(f"performance_plan.beats[{index}].hands is invalid")
        if hands.get("enabled") is True and "hand_stroke" not in chain:
            raise ValueError("enabled hands require the hand_stroke primitive")
        if hands.get("enabled") is False and "hand_stroke" in chain:
            raise ValueError("disabled hands cannot use the hand_stroke primitive")
    return deepcopy(reference), deepcopy(primitive_library)


def _validate_subject_orientation(view_mode, orientation):
    expected = {
        "front": {
            "torso_yaw_degrees": 0,
            "head_yaw_degrees": 0,
            "turn_direction": "front",
            "gaze_anchor": "camera_lens",
        },
        "three_quarter_left_45": {
            "torso_yaw_degrees": 45,
            "head_yaw_degrees": 45,
            "turn_direction": "toward_frame_left",
            "gaze_anchor": "off_camera_same_direction",
        },
        "three_quarter_right_45": {
            "torso_yaw_degrees": 45,
            "head_yaw_degrees": 45,
            "turn_direction": "toward_frame_right",
            "gaze_anchor": "off_camera_same_direction",
        },
    }
    if view_mode not in expected:
        raise ValueError(f"unknown view_mode: {view_mode}")
    if orientation != expected[view_mode]:
        raise ValueError("subject orientation must match the selected view mode")


def _require_nonempty_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _require_opaque_id(value, label):
    if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
        raise ValueError(f"{label} must be a stable opaque ID")
    lowered = value.lower()
    if "api" in lowered or "token" in lowered or lowered.startswith("sk-"):
        raise ValueError(f"{label} must not contain credential material")


def _require_standard_json(value, label, active=None):
    if active is None:
        active = set()
    if type(value) in {dict, list}:
        identity = id(value)
        if identity in active:
            raise ValueError(f"{label} contains a cyclic JSON container")
        active.add(identity)
        try:
            nested_values = value.values() if type(value) is dict else value
            if type(value) is dict and any(type(key) is not str for key in value):
                raise ValueError(f"{label} must use JSON string keys")
            for nested in nested_values:
                _require_standard_json(nested, label, active)
        finally:
            active.remove(identity)
        return
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f"{label} must contain finite JSON numbers")
    if type(value) not in {str, int, float, bool, type(None)}:
        raise ValueError(f"{label} must contain standard JSON values")


def _ensure_strict_json(value):
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("HeyGen plugin plan must be strict JSON") from error
