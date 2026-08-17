#!/usr/bin/env python3
"""Write a deterministic structured HeyGen plugin job without network calls."""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhflow.planner import DurationOutOfRangeError, build_job_plan
from scripts.dhflow.registry import load_registry
from scripts.dhflow.state import apply_auto_defaults, create_state


ARTIFACTS = {
    "task.json": "task",
    "content-beats.json": "content_beats",
    "voice-plan.json": "voice_plan",
    "visual-plan.json": "visual_plan",
    "performance-plan.json": "performance_plan",
    "heygen-app-plan.json": "heygen_app_plan",
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Create a provider-neutral digital-human job plan."
    )
    parser.add_argument("--script", required=True, help="UTF-8 script file")
    parser.add_argument("--registry", required=True, help="Asset registry JSON file")
    parser.add_argument("--out", required=True, help="New output job directory")
    parser.add_argument("--overrides", help="Optional task override JSON file")
    parser.add_argument("--voice-alias", help="Authorized registry voice alias")
    parser.add_argument("--identity-alias", help="Authorized registry identity alias")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Lock full-auto defaults: MiniMax, no company material, original_image1, no preview",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Assert network-free planning mode; this CLI never performs external actions",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    _configure_utf8_stdio()
    args = parse_args(argv)
    try:
        script = Path(args.script).read_text(encoding="utf-8")
        registry = load_registry(args.registry)
        overrides = _load_overrides(args.overrides)
        plan = build_job_plan(
            script,
            registry,
            overrides,
            voice_alias=args.voice_alias,
            identity_alias=args.identity_alias,
            operating_mode="auto" if args.auto else "interactive",
        )
        _write_job(Path(args.out), plan, auto=args.auto)
    except DurationOutOfRangeError as error:
        print(json.dumps(error.status, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(Path(args.out))
    return 0


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


def _load_overrides(path):
    if path is None:
        return {}
    overrides = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(overrides, dict):
        raise ValueError("overrides file must contain a JSON object")
    return overrides


def _write_job(output_path: Path, plan: dict, *, auto=False) -> None:
    if output_path.exists():
        raise ValueError(f"refusing to overwrite existing job directory: {output_path}")
    state = create_state(status="planned")
    if auto:
        state = apply_auto_defaults(state)
    documents = {
        filename: plan[key]
        for filename, key in ARTIFACTS.items()
    }
    documents["state.json"] = state

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(
        tempfile.mkdtemp(prefix=f".{output_path.name}-", dir=output_path.parent)
    )
    try:
        for filename, document in documents.items():
            (temporary_path / filename).write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        temporary_path.replace(output_path)
    except Exception:
        shutil.rmtree(temporary_path, ignore_errors=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
