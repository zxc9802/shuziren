"""Deterministic voice delivery plans for semantic script beats."""


from scripts.dhflow.content_director import ROLES


_DELIVERY_BY_ROLE = {
    "hook": {"speed": "brisk", "pause_before": "short", "pause_after": "short", "emphasis": "key"},
    "question": {"speed": "measured", "pause_before": "medium", "pause_after": "medium", "emphasis": "question_core"},
    "explanation": {"speed": "natural", "pause_before": "short", "pause_after": "short", "emphasis": "key"},
    "warning": {"speed": "deliberate", "pause_before": "medium", "pause_after": "medium", "emphasis": "risk"},
    "contrast": {"speed": "measured", "pause_before": "short", "pause_after": "short", "emphasis": "after_turn"},
    "steps": {"speed": "natural", "pause_before": "short", "pause_after": "short", "emphasis": "ordinal"},
    "conclusion": {"speed": "measured", "pause_before": "medium", "pause_after": "medium", "emphasis": "action"},
}
_SPEED_LEVELS = {"deliberate": 0, "measured": 1, "natural": 2, "brisk": 3}
_SPEED_BY_LEVEL = {level: speed for speed, level in _SPEED_LEVELS.items()}


def plan_voice(beats, persona: str) -> dict:
    """Return a voice plan that preserves beat content and normalizes speed changes."""
    if not isinstance(persona, str) or not persona.strip():
        raise ValueError("persona must be a non-empty string")
    if not isinstance(beats, list):
        raise ValueError("beats must be a list")
    if not beats:
        raise ValueError("beats must contain at least one beat")

    segments = []
    previous_level = None
    for index, beat in enumerate(beats):
        _validate_beat(beat, index)
        delivery = dict(_DELIVERY_BY_ROLE[beat["role"]])
        delivery["speed"] = _normalized_speed(delivery["speed"], previous_level)
        delivery["emotion"] = "calm"
        previous_level = _SPEED_LEVELS[delivery["speed"]]
        segments.append(
            {
                "id": beat["id"],
                "text": beat["text"],
                "role": beat["role"],
                "delivery": delivery,
            }
        )
    return {"persona": persona, "segments": segments}


def _validate_beat(beat, index: int) -> None:
    prefix = f"beats[{index}]"
    if not isinstance(beat, dict):
        raise ValueError(f"{prefix} must be a dict")
    for field in ("id", "text", "role"):
        value = beat.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{prefix}.{field} must be a non-empty string")
    if beat["role"] not in ROLES:
        raise ValueError(f"{prefix}.role is unknown: {beat['role']}")


def _normalized_speed(speed: str, previous_level):
    level = _SPEED_LEVELS[speed]
    if previous_level is None:
        return speed
    return _SPEED_BY_LEVEL[max(previous_level - 1, min(level, previous_level + 1))]
