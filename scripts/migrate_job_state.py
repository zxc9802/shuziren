#!/usr/bin/env python3
"""Safely migrate a digital-human job-state JSON file to version 3."""

import argparse
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhflow.state import migrate_v1, migrate_v2


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Migrate a job-state JSON file. By default, write a new sibling named "
            "<input>.migrated.json and leave the input unchanged."
        )
    )
    parser.add_argument("input", help="Existing v1 job-state JSON file")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument(
        "--output", help="New output file (must not already exist)"
    )
    destination.add_argument(
        "--in-place",
        action="store_true",
        help="Replace the input only after creating a timestamped backup",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    _configure_utf8_stdio()
    args = parse_args(argv)
    source = Path(args.input)
    try:
        source_bytes, source_identity = _read_source_snapshot(source)
        old = _decode_json(source_bytes, source)
        preservation = "exact-byte-backup" if args.in_place else "original-source"
        migrate = migrate_v2 if old.get("version") == 2 else migrate_v1
        migrated = migrate(
            old, source_bytes=source_bytes, legacy_preservation=preservation
        )
        output_bytes = _encode_json(migrated)

        if args.in_place:
            _backup_source(source, source_bytes)
            _atomic_replace_if_unchanged(
                source,
                output_bytes,
                source_bytes,
                source_identity,
            )
            destination = source
        else:
            destination = Path(args.output) if args.output else _default_output(source)
            _atomic_create(destination, output_bytes)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(destination)
    return 0


def _decode_json(contents: bytes, source: Path):
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"input is not UTF-8 JSON: {source}") from error
    try:
        return json.loads(
            text,
            parse_constant=_reject_nonfinite_constant,
            object_pairs_hook=_reject_duplicate_object_keys,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"malformed JSON in job state: {source}") from error


def _reject_nonfinite_constant(_value):
    raise ValueError("non-finite numbers are not valid JSON")


def _reject_duplicate_object_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key is not allowed")
        result[key] = value
    return result


def _encode_json(document) -> bytes:
    try:
        text = json.dumps(
            document,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "migrated state must contain only standard JSON values"
        ) from error
    return (text + "\n").encode("utf-8")


def _default_output(source: Path) -> Path:
    if source.suffix:
        return source.with_name(f"{source.stem}.migrated{source.suffix}")
    return source.with_name(f"{source.name}.migrated.json")


def _backup_source(source: Path, contents: bytes) -> Path:
    timestamp = _timestamp()
    for collision_index in range(10000):
        suffix = "" if collision_index == 0 else f"-{collision_index}"
        backup = source.with_name(f"{source.name}.{timestamp}{suffix}.bak")
        try:
            _atomic_create(backup, contents)
            return backup
        except FileExistsError:
            continue
    raise OSError("could not allocate a collision-free backup name")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")


def _atomic_create(destination: Path, contents: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = None
    created = False
    try:
        descriptor = os.open(destination, flags, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as file:
            descriptor = None
            file.write(contents)
            file.flush()
            os.fsync(file.fileno())
    except FileExistsError:
        raise FileExistsError(f"refusing to overwrite existing file: {destination}")
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _atomic_replace_if_unchanged(
    destination: Path,
    contents: bytes,
    expected_contents: bytes,
    expected_identity,
) -> None:
    temporary = _write_temporary(destination.parent, destination.name, contents)
    try:
        try:
            current_contents, current_identity = _read_source_snapshot(destination)
        except OSError as error:
            raise ValueError("source changed during migration") from error
        if (
            current_contents != expected_contents
            or current_identity != expected_identity
        ):
            raise ValueError("source changed during migration")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _read_source_snapshot(source: Path):
    if source.is_symlink():
        raise ValueError("symbolic link sources are not allowed")
    path_stat = source.lstat()
    if not stat.S_ISREG(path_stat.st_mode):
        raise ValueError("source must be a regular file")

    with source.open("rb") as file:
        before = os.fstat(file.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("source must be a regular file")
        contents = file.read()
        after = os.fstat(file.fileno())

    path_identity = _file_object_identity(path_stat)
    opened_identity = _file_object_identity(before)
    before_identity = _file_identity(before)
    after_identity = _file_identity(after)
    if (
        path_identity != opened_identity
        or before_identity != after_identity
        or len(contents) != after.st_size
    ):
        raise ValueError("source changed during migration")
    return contents, after_identity


def _file_identity(file_stat):
    return (
        file_stat.st_dev,
        file_stat.st_ino,
        file_stat.st_mode,
        file_stat.st_size,
        file_stat.st_mtime_ns,
    )


def _file_object_identity(file_stat):
    return (
        file_stat.st_dev,
        file_stat.st_ino,
        file_stat.st_mode,
    )


def _write_temporary(parent: Path, name: str, contents: bytes) -> Path:
    descriptor, raw_path = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=parent)
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(contents)
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


if __name__ == "__main__":
    raise SystemExit(main())
