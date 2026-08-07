import argparse
import sys
from pathlib import Path

from dhflow.registry import write_registry


def parse_args():
    parser = argparse.ArgumentParser(description="Create a digital human asset registry.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--avatar-group-id", required=True)
    parser.add_argument("--voice-source", required=True)
    parser.add_argument("--image-source", required=True)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main():
    _configure_utf8_output()
    args = parse_args()
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_registry(
            output_path,
            voice_id=args.voice_id,
            avatar_group_id=args.avatar_group_id,
            voice_source=args.voice_source,
            image_source=args.image_source,
            authorized=args.authorized,
            exclusive=not args.force,
        )
    except FileExistsError as error:
        raise SystemExit(f"refusing to overwrite existing file: {output_path}") from error
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(output_path)


def _configure_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


if __name__ == "__main__":
    main()
