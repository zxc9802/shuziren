"""Deterministic assembly of provider-neutral digital-human job plans."""

import json
import re
import unicodedata
from copy import deepcopy

from scripts.dhflow.content_director import analyze_script
from scripts.dhflow.heygen_web import build_web_submission_plan
from scripts.dhflow.performance_director import plan_performance
from scripts.dhflow.registry import resolve_assets
from scripts.dhflow.visual_director import plan_visual
from scripts.dhflow.voice_director import plan_voice


MIN_DURATION_SECONDS = 15.0
_SPOKEN_WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_ALLOWED_VISUAL_OVERRIDES = frozenset(
    {
        "wardrobe",
        "background",
        "scene",
        "lighting",
        "props",
        "framing",
        "aspect_ratio",
        "platform",
        "resolution",
        "pose",
        "camera",
        "safe_areas",
        "image_qa_requirements",
        "view_mode",
    }
)
_ALLOWED_NESTED_OVERRIDES = {
    "pose": frozenset({"posture", "lead_hand_side"}),
    "camera": frozenset({"lens", "angle", "height"}),
    "safe_areas": frozenset({"platform_margin"}),
}
_STRING_OVERRIDE_FIELDS = _ALLOWED_VISUAL_OVERRIDES - frozenset(
    {*_ALLOWED_NESTED_OVERRIDES, "props", "image_qa_requirements"}
)
_STRING_LIST_OVERRIDE_FIELDS = frozenset({"props", "image_qa_requirements"})
_REGISTRY_OWNED_NAMES = frozenset(
    {
        "source",
        "provider",
        "provider_id",
        "provider_voice_id",
        "voice_id",
        "authorized",
        "authorization",
        "persona",
        "voice_alias",
        "identity_alias",
        "defaults",
        "performance_profile",
        "profile",
        "hand_topology",
        "topology",
    }
)


class DurationOutOfRangeError(ValueError):
    """Raised with a rewrite suggestion when estimated speech is too short."""

    def __init__(self, status: dict):
        self.status = status
        super().__init__(
            f"estimated duration {status['estimated_duration_seconds']:.2f}s is below "
            f"the {MIN_DURATION_SECONDS:.0f}s minimum"
        )


def estimate_duration_seconds(script: str) -> float:
    """Estimate duration from CJK ideographs, spoken digits, and English-like words."""
    if not isinstance(script, str) or not script.strip():
        raise ValueError("script must be a non-empty string")
    chinese_characters = sum(_is_cjk_ideograph(character) for character in script)
    spoken_digits = sum(character.isdigit() for character in script)
    spoken_words = len(_SPOKEN_WORD.findall(script))
    return round((chinese_characters + spoken_digits) / 4.0 + spoken_words / 2.5, 2)


def _is_cjk_ideograph(character: str) -> bool:
    name = unicodedata.name(character, "")
    return name.startswith(("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-"))


def build_job_plan(
    script, registry, overrides, *, voice_alias=None, identity_alias=None,
    operating_mode="interactive",
) -> dict:
    """Build all reusable director plans without network calls or provider secrets."""
    if operating_mode not in {"interactive", "auto"}:
        raise ValueError("operating_mode must be interactive or auto")
    if not isinstance(overrides, dict):
        raise ValueError("overrides must be a dict")
    _validate_overrides(overrides)

    estimated_duration = estimate_duration_seconds(script)
    _require_supported_duration(script, estimated_duration)
    assets = resolve_assets(
        registry, voice_alias=voice_alias, identity_alias=identity_alias
    )
    beats = analyze_script(script)
    identity = assets["identity"]
    profile = identity["performance_profile"]
    hand_topology = identity.get("hand_topology", "separated")
    ordinary_overrides = deepcopy(overrides)
    if operating_mode == "auto":
        view_mode = ordinary_overrides.get("view_mode", "front")
        if view_mode != "front":
            raise ValueError("auto mode requires front original_image1")
        ordinary_overrides["view_mode"] = "front"
    visual_overrides = {
        "aspect_ratio": "9:16",
        "resolution": "720p",
        **ordinary_overrides,
    }

    voice_plan = plan_voice(beats, persona=assets["voice"]["persona"])
    visual_plan = plan_visual(
        role_summary=[beat["role"] for beat in beats],
        overrides=visual_overrides,
        identity_alias=assets["image_alias"],
        hand_topology=hand_topology,
    )
    performance_plan = plan_performance(
        beats,
        hand_topology=hand_topology,
        profile=profile,
        view_mode=visual_plan["view_mode"],
    )
    heygen_app_plan = build_web_submission_plan(
        script=script,
        voice_plan=voice_plan,
        visual_plan=visual_plan,
        performance_plan=performance_plan,
        voice_id=assets["voice"]["voice_id"],
        avatar_group_id=identity["avatar_group_id"],
    )
    plan = {
        "task": {
            "script": script,
            "estimated_duration_seconds": estimated_duration,
            "duration_status": "ready",
            "rewrite_suggestion": None,
            "voice_alias": assets["voice_alias"],
            "identity_alias": assets["image_alias"],
            **_task_route_fields(operating_mode),
            "view_mode": visual_plan["view_mode"],
            "aspect_ratio": visual_plan["aspect_ratio"],
            "raw_review_resolution": visual_plan["resolution"],
            "overrides": ordinary_overrides,
        },
        "content_beats": beats,
        "voice_plan": voice_plan,
        "visual_plan": visual_plan,
        "performance_plan": performance_plan,
        "heygen_app_plan": heygen_app_plan,
    }
    try:
        json.dumps(plan, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("job plan must be JSON-serializable") from error
    return plan


def _task_route_fields(operating_mode: str) -> dict:
    if operating_mode == "auto":
        return {
            "operating_mode": "auto",
            "voice_provider": "minimax",
            "material_route": "none",
            "image_generation_choice": "use_original",
            "selected_image_source": "original_image1",
            "preview_choice": "disabled",
        }
    return {
        "operating_mode": "interactive",
        "voice_provider": "pending",
        "material_route": "pending",
        "image_generation_choice": "pending",
        "selected_image_source": "pending",
        "preview_choice": "pending",
    }


def _validate_overrides(overrides: dict) -> None:
    for key, value in overrides.items():
        if not isinstance(key, str) or key not in _ALLOWED_VISUAL_OVERRIDES:
            raise ValueError(f"unsupported override field: {key}")
        _reject_registry_owned_keys(value, key)
        if key in _STRING_OVERRIDE_FIELDS:
            _require_non_empty_string(value, key)
            continue
        if key in _STRING_LIST_OVERRIDE_FIELDS:
            _validate_string_list(value, key)
            continue
        allowed_nested_fields = _ALLOWED_NESTED_OVERRIDES.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"override field {key} must be an object")
        for nested_key, nested_value in value.items():
            if not isinstance(nested_key, str) or nested_key not in allowed_nested_fields:
                raise ValueError(f"unsupported override field: {key}.{nested_key}")
            _require_non_empty_string(nested_value, f"{key}.{nested_key}")


def _validate_string_list(value, path: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"override field {path} must be a list of strings")
    for index, item in enumerate(value):
        _require_non_empty_string(item, f"{path}[{index}]")


def _require_non_empty_string(value, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"override field {path} must be a non-empty string")


def _reject_registry_owned_keys(value, path: str, active_containers=None) -> None:
    if not isinstance(value, (dict, list)):
        return
    if active_containers is None:
        active_containers = set()
    container_id = id(value)
    if container_id in active_containers:
        raise ValueError(f"cyclic override container at {path}")
    active_containers.add(container_id)
    try:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                nested_path = f"{path}.{key}"
                if isinstance(key, str) and key.strip().lower() in _REGISTRY_OWNED_NAMES:
                    raise ValueError(f"registry-owned field is not an override: {nested_path}")
                _reject_registry_owned_keys(nested_value, nested_path, active_containers)
        else:
            for index, item in enumerate(value):
                _reject_registry_owned_keys(item, f"{path}[{index}]", active_containers)
    finally:
        active_containers.remove(container_id)


def _require_supported_duration(script: str, estimated_duration: float) -> None:
    if estimated_duration >= MIN_DURATION_SECONDS:
        return
    raise DurationOutOfRangeError(
        {
            "status": "needs_script_confirmation",
            "reason": "estimated_duration_too_short",
            "estimated_duration_seconds": estimated_duration,
            "allowed_duration_seconds": {
                "minimum": MIN_DURATION_SECONDS,
                "maximum": None,
            },
            "rewrite_suggestion": (
                "Expand the script before planning; the original script was not changed."
            ),
            "script": script,
        }
    )
