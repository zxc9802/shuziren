"""Diagnostic talking-head motion analysis without identity or pixel matching."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path


_RELATIONSHIP_FIELDS = (
    "upper_face_to_mouth",
    "head_to_hands",
    "shoulders_to_hands",
    "torso_to_hands",
)
_SKILL_ROOT = Path(__file__).resolve().parents[2]
_VISION_FACE_SCRIPT = _SKILL_ROOT / "scripts" / "detect_face_boxes.swift"


def compare_performance_features(reference: dict, candidate: dict) -> dict:
    """Compare motion relationships, never visual identity or pixel similarity."""
    reference_motion = _motion_summary(reference, "reference")
    candidate_motion = _motion_summary(candidate, "candidate")
    relative = {}
    for field in _RELATIONSHIP_FIELDS:
        baseline = _nonnegative(reference_motion.get(field), f"reference.motion.{field}")
        observed = _nonnegative(candidate_motion.get(field), f"candidate.motion.{field}")
        relative[field] = round(observed / max(baseline, 1e-6), 3)

    findings = []
    weak_body_channels = [
        field
        for field in ("head_to_hands", "shoulders_to_hands", "torso_to_hands")
        if relative[field] < 0.58
    ]
    isolated_reference = _fraction(
        reference_motion.get("isolated_hand_rate"), "reference.motion.isolated_hand_rate"
    )
    isolated_candidate = _fraction(
        candidate_motion.get("isolated_hand_rate"), "candidate.motion.isolated_hand_rate"
    )
    if len(weak_body_channels) >= 2 or isolated_candidate > max(
        0.32, isolated_reference + 0.22
    ):
        findings.append(
            {
                "code": "hands_move_without_whole_person",
                "severity": "critical",
                "evidence": {
                    "weak_relative_channels": weak_body_channels,
                    "candidate_isolated_hand_rate": isolated_candidate,
                    "reference_isolated_hand_rate": isolated_reference,
                },
            }
        )

    if relative["upper_face_to_mouth"] < 0.58:
        findings.append(
            {
                "code": "lip_only_face_risk",
                "severity": "critical",
                "evidence": {
                    "candidate_to_reference_ratio": relative["upper_face_to_mouth"],
                    "candidate_upper_face_to_mouth": candidate_motion[
                        "upper_face_to_mouth"
                    ],
                    "reference_upper_face_to_mouth": reference_motion[
                        "upper_face_to_mouth"
                    ],
                },
            }
        )

    freeze_reference = _fraction(
        reference_motion.get("nonmouth_freeze_ratio"),
        "reference.motion.nonmouth_freeze_ratio",
    )
    freeze_candidate = _fraction(
        candidate_motion.get("nonmouth_freeze_ratio"),
        "candidate.motion.nonmouth_freeze_ratio",
    )
    if freeze_candidate > max(0.26, freeze_reference + 0.18):
        findings.append(
            {
                "code": "living_idle_collapse",
                "severity": "critical",
                "evidence": {
                    "candidate_nonmouth_freeze_ratio": freeze_candidate,
                    "reference_nonmouth_freeze_ratio": freeze_reference,
                },
            }
        )

    periodic_reference = _fraction(
        reference_motion.get("periodicity_peak"), "reference.motion.periodicity_peak"
    )
    periodic_candidate = _fraction(
        candidate_motion.get("periodicity_peak"), "candidate.motion.periodicity_peak"
    )
    if periodic_candidate > max(0.58, periodic_reference + 0.24):
        findings.append(
            {
                "code": "periodic_motion_risk",
                "severity": "warning",
                "evidence": {
                    "candidate_periodicity_peak": periodic_candidate,
                    "reference_periodicity_peak": periodic_reference,
                },
            }
        )

    severities = {finding["severity"] for finding in findings}
    if "critical" in severities:
        status = "fail"
        recommendation = "reject_and_rerender"
    elif findings:
        status = "review"
        recommendation = "manual_review_required"
    else:
        status = "diagnostic_clear"
        recommendation = "eligible_for_human_review"
    return {
        "mode": "performance_relationship_not_pixel_similarity",
        "status": status,
        "recommendation": recommendation,
        "automatic_final_approval_forbidden": True,
        "relative_to_reference": relative,
        "findings": findings,
        "limitations": [
            "Different identity, framing, wardrobe, background, and aspect ratio are intentionally ignored.",
            "Region motion is diagnostic evidence, not a provider motion target or proof of human naturalness.",
            "A human still reviews eyes, mouth shape, anatomy, identity stability, and overall performance.",
        ],
    }


def analyze_video_motion(
    path: Path, *, sample_fps: float = 4.0, max_analysis_seconds: float | None = None
) -> dict:
    """Measure normalized regional motion relationships from a local video."""
    cv2, np = _vision_modules()
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"video file not found: {source}")
    if not math.isfinite(sample_fps) or not 1.0 <= sample_fps <= 12.0:
        raise ValueError("sample_fps must be between 1 and 12")
    if max_analysis_seconds is not None and (
        not math.isfinite(max_analysis_seconds) or max_analysis_seconds <= 1
    ):
        raise ValueError("max_analysis_seconds must be greater than 1 when provided")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"could not open video: {source}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / source_fps if source_fps > 0 and frame_count > 0 else 0.0
    if duration <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError(f"video metadata is incomplete: {source}")
    analyzed_duration = (
        duration
        if max_analysis_seconds is None
        else min(duration, float(max_analysis_seconds))
    )
    sample_count = max(8, int(math.floor(analyzed_duration * sample_fps)) + 1)
    timestamps = np.linspace(0.0, analyzed_duration, sample_count, endpoint=False)
    frames = []
    actual_timestamps = []
    for timestamp in timestamps:
        capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            continue
        target_width = 320
        target_height = max(2, round(frame.shape[0] * target_width / frame.shape[1]))
        frames.append(cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA))
        actual_timestamps.append(float(timestamp))
    capture.release()
    if len(frames) < 8:
        raise ValueError(f"not enough decodable frames for performance analysis: {source}")

    face_box, face_detection = _detect_face_box(frames, cv2, np)
    regions = _regions_from_face(face_box)
    signals = {name: [] for name in regions}
    pair_timestamps = []
    previous = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for index, frame in enumerate(frames[1:], start=1):
        current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(
            previous,
            current,
            None,
            0.5,
            3,
            15,
            3,
            5,
            1.2,
            0,
        )
        magnitude = cv2.magnitude(flow[..., 0], flow[..., 1])
        for name, rect in regions.items():
            signals[name].append(_regional_motion(magnitude, rect, np))
        pair_timestamps.append(actual_timestamps[index])
        previous = current

    arrays = {name: np.asarray(values, dtype=float) for name, values in signals.items()}
    motion, diagnostics = _summarize_signals(arrays, pair_timestamps, sample_fps, np)
    return {
        "path": str(source),
        "sha256": sha256_file(source),
        "media": {
            "width": width,
            "height": height,
            "source_fps": round(source_fps, 3),
            "duration_seconds": round(duration, 3),
        },
        "analysis": {
            "sample_fps": round(float(sample_fps), 3),
            "analyzed_start_seconds": 0.0,
            "analyzed_duration_seconds": round(analyzed_duration, 3),
            "full_file_analyzed": analyzed_duration >= duration - (1.0 / source_fps),
            "sample_count": len(frames),
            "face_detection": face_detection,
            "face_box_normalized": [round(value, 4) for value in face_box],
            "regions_normalized": {
                name: [round(value, 4) for value in rect]
                for name, rect in regions.items()
            },
        },
        "motion": motion,
        "diagnostics": diagnostics,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _vision_modules():
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise ValueError("performance QC requires local Python packages cv2 and numpy") from error
    return cv2, np


def _detect_face_box(frames, cv2, np):
    boxes = []
    indexes = np.linspace(0, len(frames) - 1, min(12, len(frames)), dtype=int)
    if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data"):
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(str(cascade_path))
        for index in indexes:
            frame = frames[int(index)]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found = cascade.detectMultiScale(
                cv2.equalizeHist(gray),
                scaleFactor=1.08,
                minNeighbors=5,
                minSize=(30, 30),
            )
            if len(found) == 0:
                continue
            x, y, width, height = max(found, key=lambda box: int(box[2]) * int(box[3]))
            boxes.append(
                (
                    x / frame.shape[1],
                    y / frame.shape[0],
                    width / frame.shape[1],
                    height / frame.shape[0],
                )
            )
        method = "haar_median"
    else:
        vision_boxes = _detect_face_boxes_with_macos_vision(
            frames, indexes, cv2
        )
        if vision_boxes:
            boxes.extend(vision_boxes)
            method = "macos_vision_median"
        else:
            method = "local_skin_region_median"
        for index in indexes:
            box = _skin_face_candidate(frames[int(index)], cv2, np)
            if box is not None and not vision_boxes:
                boxes.append(box)
    if boxes:
        median = np.median(np.asarray(boxes, dtype=float), axis=0)
        return tuple(float(value) for value in median), method
    return (0.34, 0.16, 0.32, 0.27), "normalized_fallback"


def _detect_face_boxes_with_macos_vision(frames, indexes, cv2):
    swift = shutil.which("swift")
    if not swift or not _VISION_FACE_SCRIPT.is_file():
        return []
    with tempfile.TemporaryDirectory(prefix="dh-face-detect-") as directory:
        paths = []
        for position, index in enumerate(indexes):
            path = Path(directory) / f"frame-{position:02d}.png"
            if cv2.imwrite(str(path), frames[int(index)]):
                paths.append(path)
        if not paths:
            return []
        result = subprocess.run(
            [swift, str(_VISION_FACE_SCRIPT), *(str(path) for path in paths)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        try:
            records = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        boxes = []
        if not isinstance(records, list):
            return boxes
        for record in records:
            if not isinstance(record, dict):
                continue
            values = tuple(record.get(field) for field in ("x", "y", "width", "height"))
            if all(type(value) in {int, float} and math.isfinite(value) for value in values):
                boxes.append(tuple(float(value) for value in values))
        return boxes


def _skin_face_candidate(frame, cv2, np):
    """Return one upper-center skin region; this is geometry, not identity recognition."""
    height, width = frame.shape[:2]
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    lower = np.asarray([0, 130, 72], dtype=np.uint8)
    upper = np.asarray([255, 184, 142], dtype=np.uint8)
    mask = cv2.inRange(ycrcb, lower, upper)
    kernel = np.ones((5, 5), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _hierarchy = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    candidates = []
    frame_area = float(width * height)
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area_ratio = (box_width * box_height) / frame_area
        aspect = box_width / max(box_height, 1)
        center_x = (x + box_width / 2) / width
        center_y = (y + box_height / 2) / height
        if not 0.008 <= area_ratio <= 0.22:
            continue
        if not 0.42 <= aspect <= 1.55:
            continue
        if not 0.18 <= center_x <= 0.82 or center_y >= 0.62:
            continue
        center_score = 1.0 - abs(center_x - 0.5)
        upper_score = 1.0 - center_y * 0.55
        candidates.append(
            (
                area_ratio * center_score * upper_score,
                (x / width, y / height, box_width / width, box_height / height),
            )
        )
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _regions_from_face(face):
    x, y, width, height = face
    center = x + width / 2
    return {
        "mouth": _clip_rect(x + 0.12 * width, y + 0.55 * height, x + 0.88 * width, y + 0.98 * height),
        "upper_face": _clip_rect(x + 0.05 * width, y + 0.02 * height, x + 0.95 * width, y + 0.58 * height),
        "head": _clip_rect(x - 0.12 * width, y - 0.3 * height, x + 1.12 * width, y + 0.6 * height),
        "shoulders": _clip_rect(center - 1.35 * width, y + 0.8 * height, center + 1.35 * width, y + 1.65 * height),
        "torso": _clip_rect(center - 1.1 * width, y + 1.35 * height, center + 1.1 * width, y + 3.0 * height),
        "hands": _clip_rect(center - 1.9 * width, y + 1.2 * height, center + 1.9 * width, y + 4.0 * height),
    }


def _clip_rect(x0, y0, x1, y1):
    left = max(0.0, min(0.98, float(x0)))
    top = max(0.0, min(0.98, float(y0)))
    right = max(left + 0.01, min(1.0, float(x1)))
    bottom = max(top + 0.01, min(1.0, float(y1)))
    return (left, top, right, bottom)


def _regional_motion(magnitude, rect, np):
    height, width = magnitude.shape
    x0 = max(0, min(width - 1, int(rect[0] * width)))
    y0 = max(0, min(height - 1, int(rect[1] * height)))
    x1 = max(x0 + 1, min(width, int(math.ceil(rect[2] * width))))
    y1 = max(y0 + 1, min(height, int(math.ceil(rect[3] * height))))
    region = magnitude[y0:y1, x0:x1]
    finite = region[np.isfinite(region)]
    return float(np.percentile(finite, 85)) if finite.size else 0.0


def _summarize_signals(signals, timestamps, sample_fps, np):
    epsilon = 1e-6
    medians = {name: float(np.median(values)) for name, values in signals.items()}
    hands = signals["hands"]
    hand_threshold = float(np.percentile(hands, 65))
    active_hands = hands >= hand_threshold
    support = (signals["head"] + signals["shoulders"] + signals["torso"]) / 3.0
    support_to_hands = support / np.maximum(hands, epsilon)
    isolated = active_hands & (support_to_hands < 0.24)
    isolated_rate = float(np.mean(isolated[active_hands])) if np.any(active_hands) else 0.0

    mouth = signals["mouth"]
    nonmouth = (
        signals["upper_face"]
        + signals["head"]
        + signals["shoulders"]
        + signals["torso"]
    ) / 4.0
    mouth_active = mouth >= float(np.percentile(mouth, 45))
    freeze = mouth_active & ((nonmouth / np.maximum(mouth, epsilon)) < 0.28)
    freeze_ratio = float(np.mean(freeze[mouth_active])) if np.any(mouth_active) else 0.0
    periodicity = _periodicity_peak(nonmouth, sample_fps, np)

    isolation_score = hands / np.maximum(support, epsilon)
    freeze_score = mouth / np.maximum(nonmouth, epsilon)
    ranked = sorted(
        (
            (float(max(isolation_score[index], freeze_score[index])), float(timestamps[index]))
            for index in range(len(timestamps))
        ),
        reverse=True,
    )
    worst = []
    for _score, timestamp in ranked:
        if all(abs(timestamp - chosen) >= 0.75 for chosen in worst):
            worst.append(round(timestamp, 3))
        if len(worst) == 5:
            break

    motion = {
        "upper_face_to_mouth": round(medians["upper_face"] / max(medians["mouth"], epsilon), 4),
        "head_to_hands": round(medians["head"] / max(medians["hands"], epsilon), 4),
        "shoulders_to_hands": round(medians["shoulders"] / max(medians["hands"], epsilon), 4),
        "torso_to_hands": round(medians["torso"] / max(medians["hands"], epsilon), 4),
        "isolated_hand_rate": round(isolated_rate, 4),
        "nonmouth_freeze_ratio": round(freeze_ratio, 4),
        "periodicity_peak": round(periodicity, 4),
        "channel_motion_medians": {name: round(value, 5) for name, value in medians.items()},
    }
    diagnostics = {
        "worst_timestamps_seconds": worst,
        "sample_timestamps_seconds": [round(float(value), 3) for value in timestamps],
        "isolation_score": [round(float(value), 4) for value in isolation_score],
        "freeze_score": [round(float(value), 4) for value in freeze_score],
    }
    return motion, diagnostics


def _periodicity_peak(signal, sample_fps, np):
    values = np.asarray(signal, dtype=float)
    if len(values) < max(12, int(sample_fps * 3)):
        return 0.0
    centered = values - float(np.mean(values))
    energy = float(np.dot(centered, centered))
    if energy <= 1e-9:
        return 0.0
    minimum_lag = max(2, int(round(sample_fps * 0.75)))
    maximum_lag = min(len(values) - 3, int(round(sample_fps * 4.0)))
    peaks = []
    for lag in range(minimum_lag, maximum_lag + 1):
        left = centered[:-lag]
        right = centered[lag:]
        denominator = math.sqrt(float(np.dot(left, left) * np.dot(right, right)))
        if denominator > 1e-9:
            peaks.append(float(np.dot(left, right) / denominator))
    return max(0.0, max(peaks, default=0.0))


def _motion_summary(value, label):
    if not isinstance(value, dict) or not isinstance(value.get("motion"), dict):
        raise ValueError(f"{label}.motion must be a JSON object")
    return value["motion"]


def _fraction(value, label):
    result = _nonnegative(value, label)
    if result > 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _nonnegative(value, label):
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a non-negative finite number")
    return float(value)
