"""Bind semantic performance beats to exact final-audio segment boundaries."""

from __future__ import annotations

import math
import re

from scripts.dhflow.performance_director import (
    PERFORMANCE_PRIMITIVE_LIBRARY_ID,
    PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE,
    PERFORMANCE_REFERENCE_ID,
    PERFORMANCE_REFERENCE_SHA256,
    load_performance_primitive_library,
    primitive_prompt_fragments,
)


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def build_performance_beat_map(
    *,
    voice_plan: dict,
    performance_plan: dict,
    timing_document: dict,
    audio_sha256: str,
    audio_duration_seconds: float,
) -> dict:
    """Create QA checkpoints without claiming provider frame-level control."""
    _require_sha256(audio_sha256)
    duration = _positive_number(audio_duration_seconds, "audio_duration_seconds")
    voice_segments = _object_list(voice_plan, "segments", "voice_plan")
    performance_beats = _object_list(performance_plan, "beats", "performance_plan")
    timing_segments = _object_list(timing_document, "segments", "timing_document")
    if not (len(voice_segments) == len(performance_beats) == len(timing_segments)):
        raise ValueError("voice, performance, and timing segment counts must match")

    expected_reference = performance_plan.get("reference")
    if not isinstance(expected_reference, dict):
        raise ValueError("performance_plan.reference is required")
    if (
        expected_reference.get("id") != PERFORMANCE_REFERENCE_ID
        or expected_reference.get("source_sha256") != PERFORMANCE_REFERENCE_SHA256
        or expected_reference.get("scope") != "performance_only"
    ):
        raise ValueError("performance_plan.reference does not match the verified 123 source")
    expected_library = performance_plan.get("primitive_library")
    if not isinstance(expected_library, dict):
        raise ValueError("performance_plan.primitive_library is required")
    current_library, current_library_sha256 = load_performance_primitive_library()
    required_library = {
        "id": PERFORMANCE_PRIMITIVE_LIBRARY_ID,
        "version": current_library["schema_version"],
        "source": PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE,
        "source_sha256": current_library_sha256,
        "provider_timing_contract": "semantic_relative_only",
        "frame_accurate_timing_claimed": False,
        "exact_reference_timeline_copy_forbidden": True,
    }
    for field, expected in required_library.items():
        if (
            expected_library.get(field) != expected
            or type(expected_library.get(field)) is not type(expected)
        ):
            raise ValueError(f"performance_plan.primitive_library.{field} is invalid")

    output_beats = []
    previous_end = 0.0
    for index, (voice, performance, timing) in enumerate(
        zip(voice_segments, performance_beats, timing_segments, strict=True)
    ):
        prefix = f"segments[{index}]"
        expected_id = _nonempty(voice.get("id"), f"{prefix}.id")
        expected_text = voice.get("text")
        if not isinstance(expected_text, str):
            raise ValueError(f"{prefix}.text must preserve exact text")
        if performance.get("id") != expected_id or performance.get("text") != expected_text:
            raise ValueError("voice and performance beats must preserve exact text and IDs")
        if timing.get("id") != expected_id or timing.get("text") != expected_text:
            raise ValueError(f"{prefix} must preserve exact text and ID")

        start = _nonnegative_number(timing.get("start_seconds"), f"{prefix}.start_seconds")
        end = _positive_number(timing.get("end_seconds"), f"{prefix}.end_seconds")
        if end <= start:
            raise ValueError(f"{prefix} end_seconds must be after start_seconds")
        if start + 0.075 < previous_end:
            raise ValueError("timing segments must be monotonic and non-overlapping")
        if index == 0 and start > 0.075:
            raise ValueError("the first timing segment must start with the final audio")
        if end > duration + 0.075:
            raise ValueError("timing segments exceed the exact final audio duration")
        previous_end = end

        primitive_chain = performance.get("primitive_chain")
        if not isinstance(primitive_chain, list) or not primitive_chain:
            raise ValueError(f"{prefix} primitive_chain is required")
        primitive_prompt_fragments(primitive_chain)
        beat_duration = end - start
        checkpoints = [
            _checkpoint("entry", start + beat_duration * 0.12, "face_and_gaze_lead"),
            _checkpoint(
                "readable_hold",
                start + beat_duration * 0.55,
                "head_neck_shoulders_and_torso_support_the_phrase",
            ),
            _checkpoint(
                "settle",
                start + beat_duration * 0.88,
                "channels_return_to_rest_in_sequence_while_breathing_continues",
            ),
        ]
        output_beats.append(
            {
                "id": expected_id,
                "text": expected_text,
                "role": performance.get("role"),
                "start_seconds": _rounded(start),
                "end_seconds": _rounded(end),
                "duration_seconds": _rounded(beat_duration),
                "primitive_chain": list(primitive_chain),
                "provider_instruction": "semantic_relative_only",
                "qa_checkpoints": checkpoints,
            }
        )

    if abs(previous_end - duration) > 0.075:
        raise ValueError("timing segments must cover the exact final audio duration")

    timing_source = timing_document.get("source", "final_audio_segment_boundaries")
    _nonempty(timing_source, "timing_document.source")
    return {
        "schema_version": 1,
        "reference": {
            "id": expected_reference.get("id"),
            "scope": expected_reference.get("scope"),
        },
        "primitive_library": {
            "id": expected_library.get("id"),
            "source_sha256": expected_library.get("source_sha256"),
        },
        "audio": {
            "sha256": audio_sha256,
            "duration_seconds": _rounded(duration),
            "timing_source": timing_source,
        },
        "timing_scope": "planning_and_rendered_qa_only",
        "provider_frame_accurate_timing_claimed": False,
        "exact_reference_timeline_copy_forbidden": True,
        "beats": output_beats,
    }


def _checkpoint(phase: str, seconds: float, assertion: str) -> dict:
    return {
        "phase": phase,
        "seconds": _rounded(seconds),
        "assertion": assertion,
    }


def _object_list(document, field: str, label: str) -> list[dict]:
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a JSON object")
    value = document.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}.{field} must be a non-empty array")
    if any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{label}.{field} must contain JSON objects")
    return value


def _require_sha256(value: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("audio_sha256 must be 64 lowercase hexadecimal characters")


def _nonempty(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _positive_number(value, label: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return float(value)


def _nonnegative_number(value, label: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a non-negative finite number")
    return float(value)


def _rounded(value: float) -> float:
    return round(float(value), 3)
