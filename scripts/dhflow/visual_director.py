"""Deterministic, provider-neutral visual planning."""

from copy import deepcopy
from datetime import date

from scripts.dhflow.content_director import ROLES


_IDENTITY_INVARIANTS = {
    "face_shape": "preserve",
    "feature_proportions": "preserve",
    "apparent_age": "preserve",
    "skin_tone": "preserve",
    "recognizability": "preserve",
    "base_hairstyle": "preserve",
    "eyewear": "preserve",
    "body_type": "preserve",
    "long_term_persona": "preserve",
}
HAND_TOPOLOGIES = frozenset({"separated", "one_visible", "overlapping", "not_visible"})
VIEW_MODES = frozenset(
    {"front", "three_quarter_left_45", "three_quarter_right_45"}
)
_SUBJECT_ORIENTATION_BY_VIEW = {
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
_POSE_BY_TOPOLOGY = {
    "separated": {
        "anchor_hand": True,
        "lead_hand_visible": True,
        "both_hands_fully_visible": True,
        "hands_uncropped": True,
        "hands_separated": True,
        "supported_forearms": True,
        "synthetic_arms_prohibited": False,
    },
    "one_visible": {
        "anchor_hand": True,
        "lead_hand_visible": True,
        "hands_separated": False,
        "supported_forearms": True,
        "synthetic_arms_prohibited": False,
    },
    "overlapping": {
        "anchor_hand": True,
        "lead_hand_visible": True,
        "hands_separated": False,
        "supported_forearms": True,
        "synthetic_arms_prohibited": False,
    },
    "not_visible": {
        "anchor_hand": False,
        "lead_hand_visible": False,
        "hands_separated": False,
        "supported_forearms": False,
        "synthetic_arms_prohibited": True,
    },
}
_REQUIRED_SAFE_AREAS = {
    "head_motion_space": "clear",
    "subtitle_zone": "clear",
    "platform_ui_zone": "clear",
}
_COMMON_IMAGE_QA_REQUIREMENTS = (
    "identity_consistency",
    "mouth_unobstructed",
    "stable_clothing_texture",
    "low_background_interference",
    "safe_area_clearance",
    "half_body_only",
    "both_hands_fully_visible",
    "seasonal_relaxed_wardrobe",
    "background_differs_from_most_recent",
    "reference_scale_and_crop_match",
    "person_not_too_far_from_camera",
    "real_world_background_photorealism",
    "change_only_wardrobe_and_background",
)
_HAND_QA_BY_TOPOLOGY = {
    "separated": ("five_finger_structure", "correct_hand_count", "no_limb_fusion"),
    "one_visible": ("five_finger_structure", "single_visible_hand_consistency", "no_limb_fusion"),
    "overlapping": ("correct_hand_count", "overlap_topology_consistency", "no_limb_fusion"),
    "not_visible": ("no_synthetic_arms",),
}
_VIEW_QA_REQUIREMENTS = {
    "front": ("front_gaze_matches_camera",),
    "three_quarter_left_45": (
        "head_torso_and_gaze_match_45_degree_anchor",
        "no_side_eye_back_to_camera",
    ),
    "three_quarter_right_45": (
        "head_torso_and_gaze_match_45_degree_anchor",
        "no_side_eye_back_to_camera",
    ),
}
_SYSTEM_IMAGE_QA_REQUIREMENTS = frozenset(
    requirement
    for requirements in _HAND_QA_BY_TOPOLOGY.values()
    for requirement in requirements
) | frozenset(_COMMON_IMAGE_QA_REQUIREMENTS) | frozenset(
    requirement
    for requirements in _VIEW_QA_REQUIREMENTS.values()
    for requirement in requirements
)
_PROTECTED_FIELDS = {
    "identity_alias",
    "identity_master_alias",
    "identity_invariants",
    "hand_topology",
    "job_look",
    "subject_orientation",
}
_JOB_LOOK_DEFAULTS = {
    "generation_choice": "pending",
    "candidate_count": 1,
    "explicit_approval_required": True,
    "fallback": "original_image1",
    "retention": "same_identity_group",
    "selected_source": "pending",
}


def plan_visual(
    role_summary: list[str],
    overrides: dict,
    *,
    identity_alias: str = "image1",
    hand_topology: str = "overlapping",
) -> dict:
    """Return an animation-ready visual plan with safe task-level overrides."""
    _validate_inputs(role_summary, overrides, identity_alias, hand_topology)
    plan = _infer_visual(role_summary, identity_alias, hand_topology)
    _merge_overrides(plan, overrides)
    _restore_production_constraints(plan, identity_alias, hand_topology)
    return plan


def _validate_inputs(role_summary, overrides, identity_alias, hand_topology) -> None:
    if not isinstance(role_summary, list):
        raise ValueError("role_summary must be a list")
    for index, role in enumerate(role_summary):
        if not isinstance(role, str) or role not in ROLES:
            raise ValueError(f"role_summary[{index}] contains unknown role: {role}")
    if not isinstance(overrides, dict):
        raise ValueError("overrides must be a dict")
    if not isinstance(identity_alias, str) or not identity_alias.strip():
        raise ValueError("identity_alias must be a non-empty string")
    if not isinstance(hand_topology, str) or hand_topology not in HAND_TOPOLOGIES:
        raise ValueError(f"unknown hand_topology: {hand_topology}")
    view_mode = overrides.get("view_mode", "front")
    if not isinstance(view_mode, str) or view_mode not in VIEW_MODES:
        raise ValueError(f"unknown view_mode: {view_mode}")


def _infer_visual(role_summary: list[str], identity_alias: str, hand_topology: str) -> dict:
    roles = set(role_summary)
    if roles & {"warning", "conclusion"}:
        background = "quiet_real_world_professional_interior"
    elif roles & {"hook", "question"}:
        background = "warm_real_world_professional_interior"
    else:
        background = "clean_real_world_professional_interior"
    season = _local_season()

    return {
        "identity_alias": identity_alias,
        "identity_master_alias": identity_alias,
        "identity_invariants": deepcopy(_IDENTITY_INVARIANTS),
        "hand_topology": hand_topology,
        "job_look": deepcopy(_JOB_LOOK_DEFAULTS),
        "view_mode": "front",
        "subject_orientation": deepcopy(_SUBJECT_ORIENTATION_BY_VIEW["front"]),
        "composition_reference": "original_image1",
        "editable_appearance_fields": ["wardrobe", "background"],
        "season": season,
        "wardrobe": f"relaxed_{season}_casual",
        "background": background,
        "background_policy": {
            "must_differ_from_most_recent": True,
            "comparison_source": "most_recent_generated_or_adopted_job_look",
            "vary": ["environment", "dominant_materials", "color_mood"],
            "real_world_photographic_required": True,
            "reject": [
                "cgi_set",
                "futuristic_studio",
                "artificial_geometric_wall",
                "plastic_showroom",
            ],
        },
        "framing": "reference_matched_close_seated_upper_body",
        "pose": {
            "neutral_ready": True,
            "match_original_image1_seated_pose": True,
            **_POSE_BY_TOPOLOGY[hand_topology],
        },
        "mouth_visibility": "unobstructed",
        "safe_areas": _required_safe_areas(hand_topology),
        "camera": {
            "locked": True,
            "distance": "match_original_image1_close",
            "eye_level": "match_original_image1",
        },
        "image_qa_requirements": _required_qa(hand_topology),
    }


def _merge_overrides(plan: dict, overrides: dict) -> None:
    for key, value in overrides.items():
        if key in _PROTECTED_FIELDS:
            continue
        if isinstance(plan.get(key), dict) and isinstance(value, dict):
            plan[key].update(deepcopy(value))
        else:
            plan[key] = deepcopy(value)


def _restore_production_constraints(plan: dict, identity_alias: str, hand_topology: str) -> None:
    plan["identity_alias"] = identity_alias
    plan["identity_master_alias"] = identity_alias
    plan["identity_invariants"] = deepcopy(_IDENTITY_INVARIANTS)
    plan["hand_topology"] = hand_topology
    plan["job_look"] = deepcopy(_JOB_LOOK_DEFAULTS)
    view_mode = plan.get("view_mode", "front")
    if not isinstance(view_mode, str) or view_mode not in VIEW_MODES:
        raise ValueError(f"unknown view_mode: {view_mode}")
    plan["view_mode"] = view_mode
    plan["subject_orientation"] = deepcopy(_SUBJECT_ORIENTATION_BY_VIEW[view_mode])
    if not isinstance(plan.get("camera"), dict):
        plan["camera"] = {}
    if not isinstance(plan.get("pose"), dict):
        plan["pose"] = {}
    if not isinstance(plan.get("safe_areas"), dict):
        plan["safe_areas"] = {}
    extra_qa_requirements = plan.get("image_qa_requirements", [])
    if not isinstance(extra_qa_requirements, list):
        extra_qa_requirements = []
    plan["camera"]["locked"] = True
    plan["pose"].update({"neutral_ready": True, **_POSE_BY_TOPOLOGY[hand_topology]})
    plan["safe_areas"].pop("lead_hand_motion_space", None)
    plan["safe_areas"].update(_required_safe_areas(hand_topology))
    plan["mouth_visibility"] = "unobstructed"
    plan["image_qa_requirements"] = _required_qa(hand_topology, view_mode)
    plan["image_qa_requirements"].extend(
        requirement
        for requirement in extra_qa_requirements
        if isinstance(requirement, str)
        and requirement.strip()
        and requirement not in _SYSTEM_IMAGE_QA_REQUIREMENTS
    )


def _required_safe_areas(hand_topology: str) -> dict:
    safe_areas = dict(_REQUIRED_SAFE_AREAS)
    if hand_topology != "not_visible":
        safe_areas["lead_hand_motion_space"] = "clear"
    if hand_topology == "separated":
        safe_areas["both_hands_elbows_and_fingers"] = "fully_inside_frame"
    return safe_areas


def _required_qa(hand_topology: str, view_mode: str = "front") -> list[str]:
    return [
        *_COMMON_IMAGE_QA_REQUIREMENTS,
        *_HAND_QA_BY_TOPOLOGY[hand_topology],
        *_VIEW_QA_REQUIREMENTS[view_mode],
    ]


def _local_season(today: date | None = None) -> str:
    month = (today or date.today()).month
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "autumn"
    return "winter"
