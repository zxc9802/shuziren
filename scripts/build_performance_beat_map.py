#!/usr/bin/env python3
"""Create performance-beat-map.json from exact final audio and segment timing."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhflow.performance_timing import build_performance_beat_map


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Bind semantic performance beats to exact final-audio boundaries."
    )
    parser.add_argument("--voice-plan", required=True, type=Path)
    parser.add_argument("--performance-plan", required=True, type=Path)
    parser.add_argument("--timings", required=True, type=Path)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        audio = args.audio.expanduser().resolve()
        if not audio.is_file():
            raise ValueError(f"audio file not found: {audio}")
        if args.out.exists():
            raise ValueError(f"refusing to overwrite existing output: {args.out}")
        result = build_performance_beat_map(
            voice_plan=_load_json(args.voice_plan),
            performance_plan=_load_json(args.performance_plan),
            timing_document=_load_json(args.timings),
            audio_sha256=_sha256(audio),
            audio_duration_seconds=_probe_duration(audio),
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(args.out)
    return 0


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON input must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_duration(path: Path) -> float:
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
    try:
        return float(result.stdout.strip())
    except ValueError as error:
        raise ValueError("ffprobe did not return a valid audio duration") from error


if __name__ == "__main__":
    raise SystemExit(main())
