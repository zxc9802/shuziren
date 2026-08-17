"""Semantic, provider-neutral performance planning for digital humans."""

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
        "body": "stable_torso",
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
        "body": "stable_torso",
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
    expression_intensity = "moderate" if hand_topology == "overlapping" else "subtle"
    planned_beats = []
    previous_hand_action = None

    for beat in beats:
        actions = _CHANNEL_ACTIONS[beat["role"]]
        main_action = _choose_hand_action(actions["hands"], previous_hand_action, hand_topology)
        if main_action is not None:
            previous_hand_action = main_action
        planned_beats.append(
            {
                "id": beat["id"],
                "text": beat["text"],
                "role": beat["role"],
                "face": {
                    "enabled": True,
                    "action": _face_action(actions["face"], view_mode),
                    "intensity": expression_intensity,
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
                    "returns_to_center": view_mode == "front",
                    "returns_to_view_anchor": True,
                },
                "hands": _plan_hands(main_action, beat["role"], hand_topology),
                "body": {
                    "enabled": True,
                    "action": actions["body"],
                    "intensity": expression_intensity,
                    "torso_stable": True,
                },
            }
        )

    return {
        "profile": profile,
        "hand_topology": hand_topology,
        "view_mode": view_mode,
        "beats": planned_beats,
    }


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
    }
