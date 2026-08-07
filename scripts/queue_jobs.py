#!/usr/bin/env python3
"""Create and inspect a strict local FIFO digital-human job queue."""

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from migrate_job_state import (
    _atomic_create,
    _configure_utf8_stdio,
    _decode_json,
    _encode_json,
    _read_source_snapshot,
)
from scripts.dhflow.queue import create_queue, next_actionable_job, validate_queue
from scripts.dhflow.state import validate_state


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Create or inspect a sequential digital-human batch queue."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("queue", help="New queue JSON path")
    create.add_argument("job_ids", nargs="+")

    next_command = commands.add_parser("next")
    next_command.add_argument("queue", help="Existing queue JSON path")
    next_command.add_argument("--states-dir", required=True, help="Jobs root")
    return parser.parse_args(argv)


def main(argv=None):
    _configure_utf8_stdio()
    args = parse_args(argv)
    try:
        if args.command == "create":
            destination = Path(args.queue)
            _atomic_create(destination, _encode_json(create_queue(args.job_ids)))
            print(destination)
            return 0

        queue_path = Path(args.queue)
        queue_bytes, _identity = _read_source_snapshot(queue_path)
        queue = _decode_json(queue_bytes, queue_path)
        validate_queue(queue)
        states_root = Path(args.states_dir)
        statuses = {}
        for job_id in queue["job_ids"]:
            state_path = states_root / job_id / "state.json"
            state_bytes, _state_identity = _read_source_snapshot(state_path)
            state = _decode_json(state_bytes, state_path)
            validate_state(state)
            statuses[job_id] = state["status"]
        actionable = next_actionable_job(queue, statuses)
        print(actionable if actionable is not None else "blocked")
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
