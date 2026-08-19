"""302.AI IndexTTS-2 helpers. Credentials stay in the environment."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


EMOTION_ORDER = (
    "happy",
    "angry",
    "sad",
    "afraid",
    "disgusted",
    "melancholic",
    "surprised",
    "calm",
)
DEFAULT_BASE_URL = "https://api.302.ai"
CREATE_PATH = "/302/index_tts2/task"
POLL_INTERVAL_S = 2
POLL_TIMEOUT_S = 180
INTENSITY_CAP = 0.85


def verified_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


HTTPS_CONTEXT = verified_ssl_context()


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def emotion_vector(emotion: str) -> list[float]:
    name = str(emotion).strip().lower()
    if name not in EMOTION_ORDER:
        raise ValueError(f"unsupported IndexTTS emotion: {emotion}")
    return [1.0 if item == name else 0.0 for item in EMOTION_ORDER]


def resolve_emotion_vector(delivery: dict) -> list[float]:
    if "emotion_vector" not in delivery:
        return emotion_vector(delivery.get("emotion", ""))
    raw = delivery["emotion_vector"]
    if not isinstance(raw, list) or len(raw) != len(EMOTION_ORDER):
        raise ValueError("emotion_vector must contain exactly eight numbers")
    try:
        vector = [float(value) for value in raw]
    except (TypeError, ValueError) as error:
        raise ValueError("emotion_vector must contain exactly eight numbers") from error
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in vector):
        raise ValueError("emotion_vector values must be finite numbers between 0 and 1")
    if not math.isclose(sum(vector), 1.0, abs_tol=1e-6):
        raise ValueError("emotion_vector values must sum to 1")
    return vector


def emotion_alpha(intensity) -> float:
    try:
        value = float(intensity)
    except (TypeError, ValueError) as error:
        raise ValueError("emotion intensity must be a number") from error
    if value < 0:
        raise ValueError("emotion intensity must be >= 0")
    return min(value, INTENSITY_CAP)


def build_task_payload(text: str, speaker_audio_url: str, delivery: dict) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("segment text must be a non-empty string")
    if not isinstance(speaker_audio_url, str) or not speaker_audio_url.startswith(
        ("https://", "http://")
    ):
        raise ValueError("speaker_audio_url must be an http(s) URL")
    if not isinstance(delivery, dict):
        raise ValueError("delivery must be an object")
    return {
        "text": text,
        "speaker_audio_url": speaker_audio_url,
        "emotion_vector": resolve_emotion_vector(delivery),
        "emotion_alpha": emotion_alpha(delivery.get("emotion_intensity", 0)),
    }


def lossless_segments(voice_plan: dict, expected_text: str | None = None) -> list[dict]:
    if not isinstance(voice_plan, dict):
        raise ValueError("voice-plan.json must be an object")
    segments = voice_plan.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("voice-plan.json segments are required")
    joined = []
    cleaned = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"segments[{index}] must be an object")
        text = segment.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"segments[{index}].text must be exact text")
        joined.append(text)
        cleaned.append(segment)
    concatenated = "".join(joined)
    if expected_text is not None and concatenated != expected_text:
        raise ValueError("voice-plan segments are not a lossless copy of the approved text")
    return cleaned


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_duration(path: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise ValueError("ffprobe is required")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError(f"invalid audio duration: {path}")
    return duration


def concatenate_wavs(paths: list[Path], output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("ffmpeg is required")
    listing = output.with_suffix(".concat.txt")
    listing.write_text(
        "".join(f"file '{path.resolve()}'\n" for path in paths),
        encoding="utf-8",
    )
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        listing.unlink(missing_ok=True)


class IndexTTS302:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        if not api_key:
            raise ValueError("INDEXTTS_302_API_KEY is missing")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def create_and_wait(self, payload: dict) -> dict:
        task_id = self._create(payload)
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            result = self._get(task_id)
            state = result.get("state")
            if state == "SUCCESS":
                if not result.get("audio_url"):
                    raise ValueError("IndexTTS-2 succeeded without an audio URL")
                return result
            if state == "FAILURE":
                raise ValueError(self._redact(f"IndexTTS-2 failed: {result}"))
            time.sleep(POLL_INTERVAL_S)
        raise ValueError(f"IndexTTS-2 timed out waiting for task {task_id}")

    def download(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "indextts-skill"})
        try:
            with urllib.request.urlopen(
                request, context=HTTPS_CONTEXT, timeout=60
            ) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            raise ValueError(self._redact(f"audio download failed: {error}")) from error
        if not body:
            raise ValueError("IndexTTS-2 returned an empty audio file")
        dest.write_bytes(body)

    def _create(self, payload: dict) -> str:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + CREATE_PATH,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        raw = self._read_json(request)
        task_id = raw.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(self._redact(f"IndexTTS-2 create returned no task_id: {raw}"))
        return task_id

    def _get(self, task_id: str) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{CREATE_PATH}?task_id={urllib.parse.quote(task_id)}",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        return self._read_json(request)

    def _read_json(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(
                request, context=HTTPS_CONTEXT, timeout=60
            ) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ValueError(self._redact(f"IndexTTS-2 HTTP {error.code}: {detail}")) from error
        if not isinstance(raw, dict):
            raise ValueError("IndexTTS-2 returned a non-object response")
        return raw

    def _redact(self, text: str) -> str:
        return text.replace(self.api_key, "[redacted]")
