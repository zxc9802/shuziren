#!/usr/bin/env python3
"""Generate four identity-preserving boss-look candidates via OpenLux."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://api.openlux.ai/v1"
DEFAULT_MODEL = "gpt-image-2-c"
DEFAULT_SIZE = "1024x1792"
FALLBACK_SIZE = "1024x1536"
DEFAULT_QUALITY = "high"
TIMEOUT_S = 180
RETRY_STATUSES = {429, 500, 502, 503, 504}


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[redacted]")


class MultipartForm:
    def __init__(self) -> None:
        self.boundary = f"----OpenLux{uuid.uuid4().hex}"
        self._parts: list[bytes] = []

    def add_field(self, name: str, value: str) -> None:
        self._parts.append(
            (
                f"--{self.boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")
        )

    def add_file(self, name: str, path: Path) -> None:
        mime, _ = mimetypes.guess_type(path.name)
        mime = mime or "application/octet-stream"
        header = (
            f"--{self.boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        self._parts.append(header + path.read_bytes() + b"\r\n")

    def content_type(self) -> str:
        return f"multipart/form-data; boundary={self.boundary}"

    def body(self) -> bytes:
        return b"".join(self._parts) + f"--{self.boundary}--\r\n".encode("utf-8")


def post_edit(
    *,
    base_url: str,
    api_key: str,
    model: str,
    identity_master: Path,
    prompt: str,
    size: str,
    quality: str,
) -> dict:
    form = MultipartForm()
    form.add_field("model", model)
    form.add_field("prompt", prompt)
    form.add_field("size", size)
    form.add_field("quality", quality)
    form.add_file("image", identity_master)
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/images/edits",
        data=form.body(),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": form.content_type(),
            "Accept": "application/json",
        },
    )
    last_error = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(
                redact(f"OpenLux HTTP {error.code}: {body}", api_key)
            )
            if error.code not in RETRY_STATUSES or attempt == 1:
                raise last_error from error
            time.sleep(2)
        except urllib.error.URLError as error:
            raise RuntimeError(redact(f"OpenLux transport error: {error}", api_key)) from error
    raise last_error or RuntimeError("OpenLux request failed")


def decode_image(payload: dict, api_key: str) -> bytes:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(redact(f"OpenLux returned no image data: {payload}", api_key))
    item = data[0]
    if item.get("b64_json"):
        import base64

        return base64.b64decode(item["b64_json"])
    url = item.get("url")
    if not url:
        raise RuntimeError(redact(f"OpenLux image payload missing bytes: {item}", api_key))
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_S) as response:
            body = response.read()
    except urllib.error.URLError as error:
        raise RuntimeError(redact(f"OpenLux image URL download failed: {error}", api_key)) from error
    if not body:
        raise RuntimeError("OpenLux image URL returned an empty body")
    return body


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-master", required=True, type=Path)
    parser.add_argument("--prompts-json", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--quality", default=DEFAULT_QUALITY)
    parser.add_argument("--expect-sha256", default="")
    return parser.parse_args()


def main() -> int:
    load_env(SKILL_ROOT / ".env")
    args = parse_args()
    api_key = os.environ.get("OPENLUX_API_KEY", "").strip()
    base_url = os.environ.get("OPENLUX_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = os.environ.get("OPENLUX_IMAGE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if not api_key:
        print("Missing OPENLUX_API_KEY in .env or environment.", file=sys.stderr)
        return 2
    master = args.identity_master.expanduser().resolve()
    if not master.is_file():
        print(f"Identity master not found: {master}", file=sys.stderr)
        return 2
    master_hash = sha256_file(master)
    if args.expect_sha256 and args.expect_sha256.lower() != master_hash:
        print(
            f"Identity master SHA-256 mismatch: expected {args.expect_sha256}, got {master_hash}",
            file=sys.stderr,
        )
        return 2
    spec = json.loads(args.prompts_json.read_text(encoding="utf-8"))
    candidates = spec.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 4:
        print("prompts JSON must contain exactly four candidates.", file=sys.stderr)
        return 2
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, candidate in enumerate(candidates, start=1):
        label = str(candidate.get("label") or index)
        prompt = candidate.get("prompt")
        if not prompt:
            print(f"Candidate {label} is missing prompt text.", file=sys.stderr)
            return 2
        sizes = [args.size]
        if args.size == DEFAULT_SIZE:
            sizes.append(FALLBACK_SIZE)
        payload = None
        last_error = None
        used_size = args.size
        for size in sizes:
            try:
                payload = post_edit(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    identity_master=master,
                    prompt=prompt,
                    size=size,
                    quality=args.quality,
                )
                used_size = size
                break
            except RuntimeError as error:
                last_error = error
                message = str(error).lower()
                if size == DEFAULT_SIZE and ("size" in message or "400" in message):
                    continue
                print(error, file=sys.stderr)
                return 1
        if payload is None:
            print(last_error or f"OpenLux failed for candidate {label}", file=sys.stderr)
            return 1
        image_bytes = decode_image(payload, api_key)
        out_path = out_dir / f"{label}.png"
        out_path.write_bytes(image_bytes)
        manifest.append(
            {
                "label": label,
                "gesture_signature": candidate.get("gesture_signature", ""),
                "path": str(out_path),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                "size": used_size,
                "model": model,
                "identity_master_sha256": master_hash,
            }
        )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
