#!/usr/bin/env python3
"""Create a current HeyGen-only digital-human state.json skeleton."""

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhflow.state import create_state


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="work/state.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists() and not args.force:
        raise SystemExit(f"{out} already exists; pass --force to overwrite")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(create_state(), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
