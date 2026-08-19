#!/usr/bin/env python3
"""Compare a generated talking head with the private 123 performance reference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dhflow.performance_qc import (
    analyze_video_motion,
    compare_performance_features,
    sha256_file,
)
from scripts.verify_performance_reference import REFERENCE_ID, verify_reference


def run_comparison(
    *,
    reference: Path,
    candidate: Path,
    output_dir: Path,
    sample_fps: float = 4.0,
    max_analysis_seconds: float | None = None,
) -> dict:
    verified = verify_reference()
    reference_path = Path(reference).expanduser().resolve()
    candidate_path = Path(candidate).expanduser().resolve()
    if reference_path != Path(verified["path"]).resolve():
        raise ValueError("comparison reference must be the verified private 123 artifact")
    if not candidate_path.is_file():
        raise ValueError(f"candidate video not found: {candidate_path}")
    output = Path(output_dir).expanduser().resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f"output directory must be new or empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    reference_features = analyze_video_motion(
        reference_path,
        sample_fps=sample_fps,
        max_analysis_seconds=max_analysis_seconds,
    )
    candidate_features = analyze_video_motion(
        candidate_path,
        sample_fps=sample_fps,
        max_analysis_seconds=max_analysis_seconds,
    )
    comparison = compare_performance_features(reference_features, candidate_features)
    contact_sheet = output / "comparison-contact-sheet.jpg"
    _build_contact_sheet(
        reference_path,
        candidate_path,
        reference_features,
        candidate_features,
        contact_sheet,
    )
    report = {
        "schema_version": 1,
        "reference": {
            "id": REFERENCE_ID,
            "sha256": verified["sha256"],
            "local_only": True,
            "provider_upload_forbidden": True,
            "features": reference_features,
        },
        "candidate": {
            "path": str(candidate_path),
            "sha256": sha256_file(candidate_path),
            "features": candidate_features,
        },
        "comparison": comparison,
        "review_evidence": {
            "worst_timestamps_seconds": candidate_features["diagnostics"][
                "worst_timestamps_seconds"
            ],
            "contact_sheet": str(contact_sheet),
            "normalized_progress_pairing_only": True,
        },
        "privacy": {
            "reference_stays_local": True,
            "reference_must_not_enter_public_deliverables": True,
        },
    }
    (output / "performance-qc.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "realism-review.md").write_text(
        _markdown_report(report), encoding="utf-8"
    )
    return report


def _build_contact_sheet(reference, candidate, reference_features, candidate_features, output):
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise ValueError("performance QC requires local Python packages cv2 and numpy") from error

    candidate_times = list(
        candidate_features["diagnostics"].get("worst_timestamps_seconds", [])
    )
    analyzed = candidate_features["analysis"]["analyzed_duration_seconds"]
    if not candidate_times:
        candidate_times = [analyzed * fraction for fraction in (0.1, 0.3, 0.5, 0.7, 0.9)]
    candidate_times = candidate_times[:5]
    reference_duration = reference_features["analysis"]["analyzed_duration_seconds"]
    cells = []
    for candidate_time in candidate_times:
        progress = 0.0 if analyzed <= 0 else max(0.0, min(1.0, candidate_time / analyzed))
        reference_time = progress * reference_duration
        reference_frame = _frame_at(reference, reference_time, cv2)
        candidate_frame = _frame_at(candidate, candidate_time, cv2)
        top = _fit_cell(reference_frame, 300, 220, cv2, np)
        bottom = _fit_cell(candidate_frame, 300, 220, cv2, np)
        cv2.putText(
            top,
            f"123 ref {reference_time:.2f}s",
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            bottom,
            f"candidate {candidate_time:.2f}s",
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cells.append(np.vstack([top, bottom]))
    sheet = np.hstack(cells)
    if not cv2.imwrite(str(output), sheet):
        raise ValueError(f"could not write contact sheet: {output}")


def _frame_at(path, seconds, cv2):
    capture = cv2.VideoCapture(str(path))
    capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, float(seconds)) * 1000.0)
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        raise ValueError(f"could not decode frame at {seconds:.3f}s: {path}")
    return frame


def _fit_cell(frame, width, height, cv2, np):
    scale = min(width / frame.shape[1], height / frame.shape[0])
    resized = cv2.resize(
        frame,
        (max(1, round(frame.shape[1] * scale)), max(1, round(frame.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = (width - resized.shape[1]) // 2
    y = (height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def _markdown_report(report):
    comparison = report["comparison"]
    reference_motion = report["reference"]["features"]["motion"]
    candidate_motion = report["candidate"]["features"]["motion"]
    lines = [
        "# 123 表演参考对比报告",
        "",
        f"- Status: `{comparison['status']}`",
        f"- Recommendation: `{comparison['recommendation']}`",
        "- Mode: performance relationships only; no identity, SSIM, PSNR, or pixel matching.",
        "- Automatic final approval: forbidden; human review remains required.",
        "",
        "## Motion relationships",
        "",
        "| Metric | 123 reference | Candidate | Candidate / reference |",
        "| --- | ---: | ---: | ---: |",
    ]
    for field, relative in comparison["relative_to_reference"].items():
        lines.append(
            f"| `{field}` | {reference_motion[field]:.4f} | "
            f"{candidate_motion[field]:.4f} | {relative:.3f} |"
        )
    lines.extend(["", "## Findings", ""])
    if comparison["findings"]:
        for finding in comparison["findings"]:
            lines.append(
                f"- `{finding['severity']}` `{finding['code']}`: "
                f"`{json.dumps(finding['evidence'], ensure_ascii=False, sort_keys=True)}`"
            )
    else:
        lines.append("- No automated relationship gap crossed the diagnostic threshold.")
    lines.extend(
        [
            "",
            "## Review evidence",
            "",
            f"- Worst candidate timestamps: `{report['review_evidence']['worst_timestamps_seconds']}`",
            "- Contact-sheet pairs use normalized progress only; they do not claim matching words or gestures.",
            "",
            "## Limits",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in comparison["limitations"])
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare a generated talking head with the private 123 performance reference."
    )
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--reference", type=Path, default=Path(verify_reference()["path"]))
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample-fps", type=float, default=4.0)
    parser.add_argument(
        "--max-analysis-seconds",
        type=float,
        help="Optional diagnostic cap; omitted means analyze the complete file.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    try:
        args = parse_args(argv)
        report = run_comparison(
            reference=args.reference,
            candidate=args.candidate,
            output_dir=args.out,
            sample_fps=args.sample_fps,
            max_analysis_seconds=args.max_analysis_seconds,
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": report["comparison"]["status"],
        "recommendation": report["comparison"]["recommendation"],
        "report": str(args.out / "performance-qc.json"),
    }, ensure_ascii=False))
    return 1 if report["comparison"]["recommendation"] == "reject_and_rerender" else 0


if __name__ == "__main__":
    raise SystemExit(main())
