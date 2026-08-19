"""Semantic, provider-neutral performance planning for digital humans."""

import hashlib
import json
from pathlib import Path

from scripts.dhflow.content_director import ROLES


ROLE_ACTIONS = {
    "question": ["eyebrow_lift", "small_head_tilt", "optional_open_palm"],
    "explanation": ["palm_up", "small_arc", "return_to_anchor"],
    "warning": ["brow_narrow", "brief_head_still", "optional_index_or_vertical_palm"],
    "steps": ["small_counting_beat", "return_to_anchor"],
    "contrast": ["small_lateral_separation", "return_to_center"],
    "conclusion": ["single_nod", "optional_cta_gesture", "settle"],
}

_PROFILE = "business-human-1"
PERFORMANCE_REFERENCE_ID = "business-human-123-v1"
PERFORMANCE_REFERENCE_SHA256 = (
    "bba288fd4dbece4fb30f8cc5b463d3b25b1650163044a18f55c6d75bff3148ed"
)
PERFORMANCE_REFERENCE_MANIFEST = "references/performance-reference-123.json"
PERFORMANCE_PRIMITIVE_LIBRARY_ID = "business-human-performance-primitives-v1"
PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE = "references/performance-primitives.json"
_SKILL_ROOT = Path(__file__).resolve().parents[2]
_PRIMITIVE_LIBRARY_PATH = _SKILL_ROOT / PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE
HAND_TOPOLOGIES = frozenset({"separated", "one_visible", "overlapping", "not_visible"})
VIEW_MODES = frozenset(
    {"front", "three_quarter_left_45", "three_quarter_right_45"}
)
_CHANNEL_ACTIONS = {
    "hook": {
        "face": "direct_gaze_brighten",
        "head": "micro_forward_settle",
        "hands": ("small_opening_beat", "lead_hand_settle"),
        "body": "stable_breath",
    },
    "question": {
        "face": ROLE_ACTIONS["question"][0],
        "head": ROLE_ACTIONS["question"][1],
        "hands": (ROLE_ACTIONS["question"][2], "question_palm_release"),
        "body": "stable_breath",
    },
    "explanation": {
        "face": "attentive_neutral",
        "head": "micro_nod",
        "hands": tuple(ROLE_ACTIONS["explanation"][:2]),
        "body": "quiet_weight_shift",
    },
    "warning": {
        "face": ROLE_ACTIONS["warning"][0],
        "head": ROLE_ACTIONS["warning"][1],
        "hands": (ROLE_ACTIONS["warning"][2], "vertical_palm"),
        "body": "grounded_stillness",
    },
    "steps": {
        "face": "focused_neutral",
        "head": "micro_nod",
        "hands": (ROLE_ACTIONS["steps"][0], "small_rhythmic_beat"),
        "body": "quiet_weight_shift",
    },
    "contrast": {
        "face": "measured_shift",
        "head": "small_side_reset",
        "hands": (ROLE_ACTIONS["contrast"][0], "short_lateral_cut"),
        "body": ROLE_ACTIONS["contrast"][1],
    },
    "conclusion": {
        "face": "assured_soften",
        "head": ROLE_ACTIONS["conclusion"][0],
        "hands": (ROLE_ACTIONS["conclusion"][1], "hands_settle"),
        "body": ROLE_ACTIONS["conclusion"][2],
    },
}
_RETRACT_BY_ROLE = {
    "contrast": "return_to_center",
    "conclusion": "settle",
}


def plan_performance(
    beats: list[dict],
    hand_topology: str,
    profile: str = _PROFILE,
    view_mode: str = "front",
) -> dict:
    """Build a deterministic four-channel performance plan from semantic beats."""
    _validate_inputs(beats, hand_topology, profile, view_mode)
    primitive_library, primitive_library_sha256 = load_performance_primitive_library()
    expression_intensity = "moderate" if hand_topology == "overlapping" else "subtle"
    planned_beats = []
    previous_hand_action = None

    for beat in beats:
        actions = _CHANNEL_ACTIONS[beat["role"]]
        main_action = _choose_hand_action(actions["hands"], previous_hand_action, hand_topology)
        if main_action is not None:
            previous_hand_action = main_action
        hand_plan = _plan_hands(main_action, beat["role"], hand_topology)
        primitive_chain = _primitive_chain(
            primitive_library, beat["role"], hands_enabled=hand_plan["enabled"]
        )
        planned_beats.append(
            {
                "id": beat["id"],
                "text": beat["text"],
                "role": beat["role"],
                "primitive_chain": primitive_chain,
                "face": {
                    "enabled": True,
                    "action": _face_action(actions["face"], view_mode),
                    "intensity": expression_intensity,
                    "speech_coupled": True,
                    "speech_channels": ["jaw", "cheeks", "brows", "eyelids"],
                    "gaze_anchor": (
                        "camera_lens"
                        if view_mode == "front"
                        else "off_camera_same_direction"
                    ),
                },
                "head": {
                    "enabled": True,
                    "action": actions["head"],
                    "intensity": expression_intensity,
                    "neck_and_shoulders_coupled": True,
                    "returns_to_center": view_mode == "front",
                    "returns_to_view_anchor": True,
                },
                "hands": hand_plan,
                "body": {
                    "enabled": True,
                    "action": actions["body"],
                    "intensity": expression_intensity,
                    "torso_stable": True,
                    "living_idle": True,
                    "restrained_counterweight": True,
                },
            }
        )

    return {
        "profile": profile,
        "reference": {
            "id": PERFORMANCE_REFERENCE_ID,
            "source_sha256": PERFORMANCE_REFERENCE_SHA256,
            "manifest": PERFORMANCE_REFERENCE_MANIFEST,
            "scope": "performance_only",
            "verification_required_before_spend": True,
            "provider_upload_forbidden": True,
        },
        "primitive_library": {
            "id": primitive_library["id"],
            "version": primitive_library["schema_version"],
            "source": PERFORMANCE_PRIMITIVE_LIBRARY_SOURCE,
            "source_sha256": primitive_library_sha256,
            "provider_timing_contract": primitive_library["provider_contract"]["timing"],
            "frame_accurate_timing_claimed": False,
            "exact_reference_timeline_copy_forbidden": True,
        },
        "motion_contract": {
            "whole_person_speaks": True,
            "hands_must_not_move_alone": True,
            "face_head_shoulders_torso_respond_to_speech": True,
            "channel_peaks_staggered": True,
            "repetitive_dead_silence_restarts_rejected": True,
            "diagnostic_ratios_are_not_provider_targets": True,
        },
        "hand_topology": hand_topology,
        "view_mode": view_mode,
        "beats": planned_beats,
    }


def load_performance_primitive_library() -> tuple[dict, str]:
    """Load and validate the local legal motion vocabulary and return its hash."""
    try:
        raw = _PRIMITIVE_LIBRARY_PATH.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read performance primitive library: {error}") from error
    _validate_primitive_library(data)
    return data, hashlib.sha256(raw).hexdigest()


def primitive_prompt_fragments(chain: list[str]) -> list[str]:
    """Resolve a validated primitive chain into provider-neutral prompt fragments."""
    library, _ = load_performance_primitive_library()
    by_id = {item["id"]: item["prompt_fragment"] for item in library["primitives"]}
    if not isinstance(chain, list) or not chain:
        raise ValueError("primitive chain must be a non-empty list")
    if len(chain) != len(set(chain)):
        raise ValueError("primitive chain must not contain duplicates")
    unknown = [item for item in chain if item not in by_id]
    if unknown:
        raise ValueError(f"primitive chain contains unknown primitives: {unknown}")
    if chain[0] != "living_idle" or chain[-1] != "phrase_settle":
        raise ValueError("primitive chain must start living and end with a phrase settle")
    return [by_id[item] for item in chain]


def _validate_primitive_library(data) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("performance primitive library schema_version must be 1")
    if data.get("id") != PERFORMANCE_PRIMITIVE_LIBRARY_ID:
        raise ValueError("performance primitive library id is invalid")
    if data.get("reference_id") != PERFORMANCE_REFERENCE_ID:
        raise ValueError("performance primitive library reference is invalid")
    if data.get("scope") != "performance_only":
        raise ValueError("performance primitive library scope is invalid")
    provider = data.get("provider_contract")
    if not isinstance(provider, dict):
        raise ValueError("performance primitive provider contract is required")
    expected_provider = {
        "timing": "semantic_relative_only",
        "frame_accurate_timing_claimed": False,
        "exact_reference_timeline_copy_forbidden": True,
        "provider_upload_forbidden": True,
    }
    for field, expected in expected_provider.items():
        if provider.get(field) != expected or type(provider.get(field)) is not type(expected):
            raise ValueError(f"performance primitive provider contract {field} is invalid")

    primitives = data.get("primitives")
    if not isinstance(primitives, list) or not primitives:
        raise ValueError("performance primitive library requires primitives")
    primitive_ids = []
    for index, primitive in enumerate(primitives):
        if not isinstance(primitive, dict):
            raise ValueError(f"performance primitive {index} must be an object")
        for field in ("id", "semantic_job", "prompt_fragment"):
            value = primitive.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"performance primitive {index}.{field} is required")
        channels = primitive.get("channels")
        rejects = primitive.get("reject_when")
        if not _nonempty_string_list(channels) or not _nonempty_string_list(rejects):
            raise ValueError(f"performance primitive {index} channels and rejects are required")
        primitive_ids.append(primitive["id"])
    if len(primitive_ids) != len(set(primitive_ids)):
        raise ValueError("performance primitive ids must be unique")

    chains = data.get("role_chains")
    if not isinstance(chains, dict) or set(chains) != ROLES:
        raise ValueError("performance primitive role chains must cover every semantic role")
    allowed = set(primitive_ids)
    for role, chain in chains.items():
        if not _nonempty_string_list(chain) or len(chain) != len(set(chain)):
            raise ValueError(f"performance primitive chain for {role} is invalid")
        if chain[0] != "living_idle" or chain[-1] != "phrase_settle":
            raise ValueError(f"performance primitive chain for {role} has invalid boundaries")
        if set(chain) - allowed:
            raise ValueError(f"performance primitive chain for {role} uses unknown primitives")


def _nonempty_string_list(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _primitive_chain(library: dict, role: str, *, hands_enabled: bool) -> list[str]:
    chain = list(library["role_chains"][role])
    if not hands_enabled:
        chain.remove("hand_stroke")
    primitive_prompt_fragments(chain)
    return chain


def _validate_inputs(beats, hand_topology, profile, view_mode) -> None:
    if not isinstance(profile, str) or profile != _PROFILE:
        raise ValueError(f"unknown profile: {profile}")
    if not isinstance(hand_topology, str) or hand_topology not in HAND_TOPOLOGIES:
        raise ValueError(f"unknown hand_topology: {hand_topology}")
    if not isinstance(view_mode, str) or view_mode not in VIEW_MODES:
        raise ValueError(f"unknown view_mode: {view_mode}")
    if not isinstance(beats, list) or not beats:
        raise ValueError("beats must be a non-empty list")
    for index, beat in enumerate(beats):
        prefix = f"beats[{index}]"
        if not isinstance(beat, dict):
            raise ValueError(f"{prefix} must be a dict")
        for field in ("id", "text", "role"):
            value = beat.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{prefix}.{field} must be a non-empty string")
        if beat["role"] not in ROLES:
            raise ValueError(f"{prefix}.role is unknown: {beat['role']}")


def _face_action(action: str, view_mode: str) -> str:
    if view_mode != "front" and action == "direct_gaze_brighten":
        return "off_camera_gaze_brighten"
    return action


def _choose_hand_action(candidates, previous_action, hand_topology):
    if hand_topology == "not_visible":
        return None
    for candidate in candidates:
        if candidate != previous_action:
            return candidate
    raise ValueError("each role must provide an alternative hand action")


def _plan_hands(main_action, role: str, hand_topology: str) -> dict:
    if main_action is None:
        return {
            "enabled": False,
            "intensity": "none",
            "main_action": None,
            "cycle": None,
            "anchor_hand": "out_of_frame",
            "moves_in_isolation": False,
            "must_return_to_rest": True,
        }

    intensity = {
        "separated": "restrained",
        "one_visible": "low",
        "overlapping": "minimal",
    }[hand_topology]
    return {
        "enabled": True,
        "intensity": intensity,
        "main_action": main_action,
        "cycle": {
            "prepare": "release_lead_hand_from_anchor",
            "stroke": main_action,
            "optional_hold": "brief_if_semantically_emphasized",
            "retract": _RETRACT_BY_ROLE.get(role, "return_to_anchor"),
            "cooldown": "natural_idle_before_next_trigger",
        },
        "anchor_hand": "stable",
        "moves_in_isolation": False,
        "must_return_to_rest": True,
    }
