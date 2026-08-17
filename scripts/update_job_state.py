#!/usr/bin/env python3
"""Apply one explicit, network-free event to a HeyGen job state."""

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from migrate_job_state import (
    _atomic_replace_if_unchanged,
    _backup_source,
    _configure_utf8_stdio,
    _decode_json,
    _encode_json,
    _read_source_snapshot,
)
from scripts.dhflow.state import (
    record_auto_raw_approval,
    record_image_approval,
    record_image_candidate,
    record_image_choice,
    record_original_image_selection,
    record_preview_approval,
    record_preview_choice,
    record_preview_result,
    record_raw_approval,
    record_raw_video,
    record_render_started,
    apply_auto_defaults,
    start_image_generation,
    transition,
    validate_state,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Update one local HeyGen digital-human job state atomically."
    )
    parser.add_argument("state", help="Existing state.json file")
    events = parser.add_subparsers(dest="event", required=True)

    transition_parser = events.add_parser("transition")
    transition_parser.add_argument("--to", required=True)

    events.add_parser("apply-auto-defaults")

    image_choice = events.add_parser("image-choice")
    image_mode = image_choice.add_mutually_exclusive_group(required=True)
    image_mode.add_argument("--generate-new", action="store_true")
    image_mode.add_argument("--use-original", action="store_true")

    image_candidate = events.add_parser("image-candidate")
    image_candidate.add_argument("--sha256", required=True)
    image_candidate.add_argument("--artifact-ref", required=True)

    image_approval = events.add_parser("approve-image")
    _add_approval_arguments(image_approval)

    preview_choice = events.add_parser("preview-choice")
    preview_mode = preview_choice.add_mutually_exclusive_group(required=True)
    preview_mode.add_argument("--enabled", action="store_true")
    preview_mode.add_argument("--disabled", action="store_true")

    render = events.add_parser("render-started")
    render.add_argument("--kind", choices=("preview", "full_raw"), required=True)
    render.add_argument("--video-id", required=True)
    render.add_argument("--evidence-json", required=True)

    preview_result = events.add_parser("preview-result")
    preview_result.add_argument("--video-id", required=True)
    preview_result.add_argument("--sha256", required=True)
    preview_result.add_argument("--artifact-ref", required=True)
    preview_qa = preview_result.add_mutually_exclusive_group(required=True)
    preview_qa.add_argument("--qa-passed", action="store_true")
    preview_qa.add_argument("--qa-failed", action="store_true")

    preview_approval = events.add_parser("approve-preview")
    _add_approval_arguments(preview_approval)

    raw = events.add_parser("raw-video")
    raw.add_argument("--video-id", required=True)
    raw.add_argument("--sha256", required=True)
    raw.add_argument("--artifact-ref", required=True)
    qa = raw.add_mutually_exclusive_group(required=True)
    qa.add_argument("--qa-passed", action="store_true")
    qa.add_argument("--qa-failed", action="store_true")

    approval = events.add_parser("approve-raw")
    _add_approval_arguments(approval)

    auto_raw = events.add_parser("approve-raw-auto")
    auto_raw.add_argument("--recorded-at", required=True)
    auto_raw.add_argument("--evidence-ref", required=True)
    return parser.parse_args(argv)


def _add_approval_arguments(parser):
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--recorded-at", required=True)
    parser.add_argument("--evidence-ref", required=True)


def main(argv=None) -> int:
    _configure_utf8_stdio()
    args = parse_args(argv)
    source = Path(args.state)
    try:
        source_bytes, source_identity = _read_source_snapshot(source)
        state = _decode_json(source_bytes, source)
        validate_state(state)
        updated = _apply_event(state, args)
        output_bytes = _encode_json(updated)
        _backup_source(source, source_bytes)
        _atomic_replace_if_unchanged(
            source,
            output_bytes,
            source_bytes,
            source_identity,
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(source)
    return 0


def _apply_event(state, args):
    if args.event == "transition":
        return transition(state, args.to)
    if args.event == "apply-auto-defaults":
        return apply_auto_defaults(state)
    if args.event == "image-choice":
        chosen = record_image_choice(state, generate_new=args.generate_new)
        if args.generate_new:
            return start_image_generation(chosen)
        return record_original_image_selection(chosen)
    if args.event == "image-candidate":
        return record_image_candidate(
            state,
            content_sha256=args.sha256,
            artifact_ref=args.artifact_ref,
        )
    if args.event == "approve-image":
        return record_image_approval(
            state,
            reviewer=args.reviewer,
            recorded_at=args.recorded_at,
            evidence_ref=args.evidence_ref,
        )
    if args.event == "preview-choice":
        return record_preview_choice(state, enabled=args.enabled)
    if args.event == "render-started":
        evidence_path = Path(args.evidence_json)
        evidence_bytes, _identity = _read_source_snapshot(evidence_path)
        evidence = _decode_json(evidence_bytes, evidence_path)
        if not isinstance(evidence, dict):
            raise ValueError("render evidence must be a JSON object")
        return record_render_started(
            state,
            kind=args.kind,
            video_id=args.video_id,
            evidence=evidence,
        )
    if args.event == "preview-result":
        return record_preview_result(
            state,
            video_id=args.video_id,
            content_sha256=args.sha256,
            artifact_ref=args.artifact_ref,
            qa_passed=args.qa_passed,
        )
    if args.event == "approve-preview":
        return record_preview_approval(
            state,
            reviewer=args.reviewer,
            recorded_at=args.recorded_at,
            evidence_ref=args.evidence_ref,
        )
    if args.event == "raw-video":
        return record_raw_video(
            state,
            video_id=args.video_id,
            content_sha256=args.sha256,
            artifact_ref=args.artifact_ref,
            qa_passed=args.qa_passed,
        )
    if args.event == "approve-raw":
        return record_raw_approval(
            state,
            reviewer=args.reviewer,
            recorded_at=args.recorded_at,
            evidence_ref=args.evidence_ref,
        )
    if args.event == "approve-raw-auto":
        return record_auto_raw_approval(
            state,
            recorded_at=args.recorded_at,
            evidence_ref=args.evidence_ref,
        )
    raise ValueError("unknown state event")


if __name__ == "__main__":
    raise SystemExit(main())
