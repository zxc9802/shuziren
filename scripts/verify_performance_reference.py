#!/usr/bin/env python3
"""Verify the frozen local performance reference before live generation."""

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "references" / "performance-reference-123.json"
REFERENCE_ID = "business-human-123-v1"
PROFILE = "business-human-1"


def verify_reference(manifest_path=DEFAULT_MANIFEST, *, root=ROOT) -> dict:
    manifest_path = Path(manifest_path)
    root = Path(root).resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read performance reference manifest: {error}") from error

    if not isinstance(manifest, dict):
        raise ValueError("performance reference manifest must be a JSON object")
    if manifest.get("version") != 1:
        raise ValueError("performance reference manifest version must be 1")
    if manifest.get("id") != REFERENCE_ID:
        raise ValueError(f"performance reference id must be {REFERENCE_ID}")
    if manifest.get("profile") != PROFILE:
        raise ValueError(f"performance reference profile must be {PROFILE}")

    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        raise ValueError("performance reference artifact must be an object")
    relative_path = artifact.get("relative_path")
    expected_sha256 = artifact.get("sha256")
    expected_size = artifact.get("size_bytes")
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("performance reference relative_path must be non-empty")
    if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        raise ValueError("performance reference must stay inside the skill root")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ValueError("performance reference sha256 must be 64 lowercase hex characters")
    if any(character not in "0123456789abcdef" for character in expected_sha256):
        raise ValueError("performance reference sha256 must be 64 lowercase hex characters")
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise ValueError("performance reference size_bytes must be a positive integer")

    source = (root / relative_path).resolve()
    try:
        source.relative_to(root)
    except ValueError as error:
        raise ValueError("performance reference must stay inside the skill root") from error
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"performance reference file not found: {source}")
    actual_size = source.stat().st_size
    if actual_size != expected_size:
        raise ValueError(
            f"performance reference size mismatch: expected {expected_size}, got {actual_size}"
        )
    actual_sha256 = _sha256(source)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            "performance reference SHA-256 mismatch: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )

    return {
        "status": "verified",
        "id": REFERENCE_ID,
        "profile": PROFILE,
        "sha256": actual_sha256,
        "size_bytes": actual_size,
        "path": str(source),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify the private business-human-123 performance reference."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        result = verify_reference(args.manifest)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"verified {result['id']} -> {result['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
