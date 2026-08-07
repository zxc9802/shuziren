"""Strict FIFO coordination for local digital-human batch jobs."""

import json
import re

from scripts.dhflow.state import STATES


BLOCKING_APPROVAL_STATES = frozenset(
    {
        "awaiting_image_approval",
        "awaiting_preview_approval",
        "awaiting_raw_approval",
    }
)

_JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_CREDENTIAL_MARKERS = (
    "api-key",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)


def create_queue(job_ids):
    """Return a strict queue preserving the user's exact input order."""
    queue = {"version": 1, "job_ids": list(job_ids) if isinstance(job_ids, list) else job_ids}
    validate_queue(queue)
    return queue


def validate_queue(queue):
    """Reject malformed, duplicate, URL-like, or credential-like queue entries."""
    if not isinstance(queue, dict) or set(queue) != {"version", "job_ids"}:
        raise ValueError("queue must contain only version and job_ids")
    if type(queue["version"]) is not int or queue["version"] != 1:
        raise ValueError("queue version must be 1")
    job_ids = queue["job_ids"]
    if not isinstance(job_ids, list) or not job_ids:
        raise ValueError("queue job IDs must be a non-empty array")
    seen = set()
    for job_id in job_ids:
        _validate_job_id(job_id)
        if job_id in seen:
            raise ValueError("duplicate job ID")
        seen.add(job_id)
    try:
        json.dumps(queue, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("queue must be strict JSON") from error


def next_actionable_job(queue, job_statuses):
    """Return only the FIFO head, or None while its approval gate blocks."""
    validate_queue(queue)
    if not isinstance(job_statuses, dict):
        raise ValueError("job statuses must be a JSON object")
    for job_id, status in job_statuses.items():
        _validate_job_id(job_id)
        if not isinstance(status, str) or status not in STATES:
            raise ValueError("unknown job status")
    for job_id in queue["job_ids"]:
        status = job_statuses.get(job_id)
        if status is None:
            raise ValueError(f"missing state for job ID: {job_id}")
        if status == "complete":
            continue
        if status in BLOCKING_APPROVAL_STATES:
            return None
        return job_id
    return None


def _validate_job_id(job_id):
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise ValueError("job ID must be a safe opaque ID")
    lowered = job_id.lower()
    if job_id in {".", ".."} or lowered.startswith("sk-") or any(
        marker in lowered for marker in _CREDENTIAL_MARKERS
    ):
        raise ValueError("job ID must not contain credential material")
