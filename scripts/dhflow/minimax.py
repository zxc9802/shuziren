"""MiniMax TTS payload mapping. Director metadata never leaves this layer."""

from __future__ import annotations


SUPPORTED_EMOTIONS = {
    "happy",
    "sad",
    "angry",
    "fearful",
    "disgusted",
    "surprised",
    "calm",
}
DIRECTOR_INTENSITY_CAP = 0.85


def director_intensity(segment: dict) -> float:
    if not isinstance(segment, dict):
        raise ValueError("MiniMax segment must be an object")
    raw = segment.get("director_intensity")
    if raw is None:
        raw = segment.get("emotion_intensity")
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError("director_intensity must be a number") from error
    if not 0 <= value <= DIRECTOR_INTENSITY_CAP:
        raise ValueError(
            f"director_intensity must be between 0 and {DIRECTOR_INTENSITY_CAP}"
        )
    return value


def build_task_payload(plan: dict, segment: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("MiniMax plan must be an object")
    if not isinstance(segment, dict):
        raise ValueError("MiniMax segment must be an object")

    text = segment.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("MiniMax segment text must be a non-empty string")
    model = plan.get("model")
    if not isinstance(model, str) or not model:
        raise ValueError("MiniMax model is required")
    voice_id = plan.get("resolved_voice_id")
    if not isinstance(voice_id, str) or not voice_id:
        raise ValueError("MiniMax resolved_voice_id is required")

    emotion = str(segment.get("emotion", "")).strip().lower()
    if emotion not in SUPPORTED_EMOTIONS:
        raise ValueError(f"unsupported MiniMax emotion: {emotion}")
    try:
        speed = float(segment.get("speed"))
    except (TypeError, ValueError) as error:
        raise ValueError("MiniMax speed must be a number") from error
    if not 0.5 <= speed <= 2.0:
        raise ValueError("MiniMax speed must be between 0.5 and 2.0")

    # Validate the internal marker, but intentionally omit it from the provider payload.
    director_intensity(segment)
    return {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": 1.0,
            "pitch": 0,
            "emotion": emotion,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
        "language_boost": "Chinese",
        "subtitle_enable": False,
        "output_format": "hex",
        "aigc_watermark": False,
    }
