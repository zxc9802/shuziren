#!/usr/bin/env python3
"""Synthesize a voice-plan.json through 302.AI IndexTTS-2."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhflow.indextts import (
    DEFAULT_BASE_URL,
    IndexTTS302,
    build_task_payload,
    concatenate_wavs,
    load_env,
    lossless_segments,
    probe_duration,
    sha256_file,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Synthesize approved voice-plan segments with IndexTTS-2."
    )
    parser.add_argument("--voice-plan", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--approved-text", type=Path)
    parser.add_argument("--speaker-audio-url")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    load_env(ROOT / ".env")
    try:
        speaker_url = (
            args.speaker_audio_url
            or os.environ.get("INDEXTTS_SPEAKER_AUDIO_URL", "").strip()
        )
        if not speaker_url:
            raise ValueError(
                "INDEXTTS_SPEAKER_AUDIO_URL is missing; 302.AI IndexTTS-2 needs a public speaker URL"
            )
        voice_plan = json.loads(args.voice_plan.read_text(encoding="utf-8-sig"))
        expected = (
            args.approved_text.read_text(encoding="utf-8") if args.approved_text else None
        )
        segments = lossless_segments(voice_plan, expected)
        client = IndexTTS302(
            os.environ.get("INDEXTTS_302_API_KEY", "").strip(),
            os.environ.get("INDEXTTS_302_BASE_URL", DEFAULT_BASE_URL).strip()
            or DEFAULT_BASE_URL,
        )
        out_dir = args.out_dir
        if out_dir.exists() and any(out_dir.iterdir()):
            raise ValueError(f"refusing to write into a non-empty directory: {out_dir}")
        segment_dir = out_dir / "segments"
        segment_paths = []
        timing_segments = []
        cursor = 0.0
        for segment in segments:
            payload = build_task_payload(
                segment["text"],
                speaker_url,
                segment.get("delivery") or {},
            )
            result = client.create_and_wait(payload)
            dest = segment_dir / f"{segment['id']}.wav"
            client.download(result["audio_url"], dest)
            duration = probe_duration(dest)
            timing_segments.append(
                {
                    "id": segment["id"],
                    "text": segment["text"],
                    "start_seconds": round(cursor, 3),
                    "end_seconds": round(cursor + duration, 3),
                }
            )
            cursor += duration
            segment_paths.append(dest)
        final_audio = out_dir / "exact-final-indextts.wav"
        concatenate_wavs(segment_paths, final_audio)
        final_duration = probe_duration(final_audio)
        if abs(final_duration - cursor) > 0.15:
            raise ValueError("concatenated IndexTTS-2 duration does not match segment sum")
        timings = {
            "source": "indextts_concatenated_segment_boundaries",
            "segments": timing_segments,
        }
        (out_dir / "final-audio-segments.json").write_text(
            json.dumps(timings, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "audio": str(final_audio),
                    "sha256": sha256_file(final_audio),
                    "duration_seconds": round(final_duration, 3),
                    "timings": str(out_dir / "final-audio-segments.json"),
                },
                ensure_ascii=False,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
