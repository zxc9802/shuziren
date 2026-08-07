import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.dhflow.queue import create_queue, next_actionable_job, validate_queue
from scripts.dhflow.state import create_state


ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCRIPT = ROOT / "scripts" / "queue_jobs.py"


class BatchQueueTests(unittest.TestCase):
    def test_queue_preserves_input_order(self):
        queue = create_queue(["job-1", "job-2", "job-3"])
        self.assertEqual(["job-1", "job-2", "job-3"], queue["job_ids"])
        self.assertEqual("job-1", next_actionable_job(queue, {"job-1": "planned"}))

    def test_head_waiting_for_approval_blocks_later_jobs(self):
        queue = create_queue(["job-1", "job-2"])
        states = {
            "job-1": "awaiting_image_approval",
            "job-2": "planned",
        }
        self.assertIsNone(next_actionable_job(queue, states))

    def test_completed_head_releases_next_job(self):
        queue = create_queue(["job-1", "job-2"])
        states = {"job-1": "complete", "job-2": "planned"}
        self.assertEqual("job-2", next_actionable_job(queue, states))

    def test_queue_rejects_duplicate_or_unsafe_job_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate job ID"):
            create_queue(["job-1", "job-1"])
        for unsafe in (True, "", "../job-1", "https://example.com", "sk-secret"):
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(ValueError, "job ID"):
                    validate_queue({"version": 1, "job_ids": [unsafe]})

    def test_cli_prints_only_head_or_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue_path = root / "queue.json"
            jobs = root / "jobs"
            for job_id, status in (
                ("job-1", "awaiting_preview_approval"),
                ("job-2", "planned"),
            ):
                job_dir = jobs / job_id
                job_dir.mkdir(parents=True)
                (job_dir / "state.json").write_text(
                    json.dumps(create_state(status=status)), encoding="utf-8"
                )

            created = subprocess.run(
                [
                    sys.executable,
                    str(QUEUE_SCRIPT),
                    "create",
                    str(queue_path),
                    "job-1",
                    "job-2",
                ],
                cwd=ROOT,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            next_job = subprocess.run(
                [
                    sys.executable,
                    str(QUEUE_SCRIPT),
                    "next",
                    str(queue_path),
                    "--states-dir",
                    str(jobs),
                ],
                cwd=ROOT,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(0, created.returncode, created.stderr)
            self.assertEqual(0, next_job.returncode, next_job.stderr)
            self.assertEqual("blocked", next_job.stdout.strip())
