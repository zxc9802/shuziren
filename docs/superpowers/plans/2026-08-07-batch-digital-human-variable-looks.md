# Batch Digital Human Variable Looks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execute sequentially; do not dispatch subagents.

**Goal:** Make `image1` an immutable boss identity master, optionally create and approve one script-specific look per job, and submit verified Avatar IV renders through the logged-in HeyGen web plan-credit flow without blueprint false positives.

**Architecture:** Keep script/voice/visual/performance planning provider-neutral, add an explicit per-job look contract and state gates, and replace the active API-credit action plan with a deterministic browser-submission plan plus observable render-evidence classifier. The runtime Skill drives the built-in image model and logged-in HeyGen page; pure Python modules only build/validate plans and persist resumable evidence.

**Tech Stack:** Python 3 standard library, `unittest`, JSON state/artifacts, Codex built-in image generation, Codex in-app browser control, authenticated HeyGen web account, Markdown Skill instructions.

---

## File map

- Modify `scripts/dhflow/visual_director.py`: add the immutable identity-master and per-job-look planning contract.
- Modify `scripts/dhflow/planner.py`: emit image-generation choice and selected-look fields without adding provider IDs or changing the seven-artifact layout.
- Create `scripts/dhflow/heygen_web.py`: build the logged-in web submission plan and classify observable render evidence.
- Modify `scripts/dhflow/state.py`: move to state schema v3 with image, preview, render, and approval gates.
- Modify `scripts/update_job_state.py`: expose explicit CLI events for the new gates.
- Modify `scripts/migrate_job_state.py`: migrate valid v2 states to v3 without inheriting unsafe approval authority.
- Create `scripts/dhflow/queue.py`: maintain a strict local FIFO queue whose head blocks while awaiting user approval.
- Create `scripts/queue_jobs.py`: create and inspect multi-script job queues without provider calls.
- Modify `scripts/dhflow/planner.py` and `scripts/plan_job.py`: use the browser plan while keeping output filename `heygen-app-plan.json` for artifact compatibility.
- Retire active use of `scripts/dhflow/heygen_app.py`: no generated job plan may reference API-credit speech/video actions.
- Modify `SKILL.md`: define the per-job image question, explicit image approval, browser-only plan-credit submission, motion requirements, and truthful render reporting.
- Modify `references/framework.md`, `references/checklists.md`, `references/api-facts.md`: document the v3 state, browser flow, and evidence gates.
- Create `references/browser-submission.md`: concise runtime procedure for binding assets, entering exact content, clicking Generate, and verifying real rendering.
- Modify `agents/openai.yaml`: make the default prompt mention the per-job look choice and explicit image approval.
- Modify `tests/test_directors.py`, `tests/test_planner.py`, `tests/test_state.py`: cover image planning and state gates.
- Create `tests/test_heygen_web.py`: cover the browser plan and blueprint/render classification.
- Create `tests/test_skill_contract.py`: prevent reintroduction of API-credit tools or false-positive wording.

### Task 1: Encode the identity-master and one-candidate look contract

**Files:**
- Modify: `scripts/dhflow/visual_director.py`
- Modify: `scripts/dhflow/planner.py`
- Test: `tests/test_directors.py`
- Test: `tests/test_planner.py`

- [ ] **Step 1: Write failing director tests**

Add tests asserting that the visual plan contains an immutable identity master and one candidate with approval required:

```python
def test_visual_plan_keeps_image1_as_master_and_plans_one_approved_job_look(self):
    plan = plan_visual(
        ["hook", "explanation"],
        {},
        identity_alias="image1",
        hand_topology="separated",
    )

    self.assertEqual("image1", plan["identity_master_alias"])
    self.assertEqual("pending", plan["job_look"]["generation_choice"])
    self.assertEqual(1, plan["job_look"]["candidate_count"])
    self.assertTrue(plan["job_look"]["explicit_approval_required"])
    self.assertEqual("original_image1", plan["job_look"]["fallback"])
    self.assertEqual("same_identity_group", plan["job_look"]["retention"])


def test_visual_overrides_cannot_replace_identity_master_or_approval_gate(self):
    plan = plan_visual(
        ["warning"],
        {
            "identity_master_alias": "other",
            "job_look": {"explicit_approval_required": False},
        },
        identity_alias="image1",
        hand_topology="separated",
    )

    self.assertEqual("image1", plan["identity_master_alias"])
    self.assertTrue(plan["job_look"]["explicit_approval_required"])
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run:

```powershell
python -m unittest tests.test_directors.VisualDirectorTests -v
```

Expected: FAIL because `identity_master_alias` and `job_look` do not exist and the new override fields are not accepted.

- [ ] **Step 3: Implement the minimal visual contract**

In `visual_director.py`, add protected fields and emit the job-look contract:

```python
_PROTECTED_FIELDS = {
    "identity_alias",
    "identity_master_alias",
    "identity_invariants",
    "hand_topology",
    "job_look",
}

_JOB_LOOK_DEFAULTS = {
    "generation_choice": "pending",
    "candidate_count": 1,
    "explicit_approval_required": True,
    "fallback": "original_image1",
    "retention": "same_identity_group",
    "selected_source": "pending",
}
```

Include these fields in `_infer_visual` and restore them in `_restore_production_constraints`:

```python
plan["identity_master_alias"] = identity_alias
plan["job_look"] = deepcopy(_JOB_LOOK_DEFAULTS)
```

Update `_ALLOWED_VISUAL_OVERRIDES` and `_ALLOWED_NESTED_OVERRIDES` in `planner.py` only for safe job styling; do not allow identity-master or approval fields as overrides.

- [ ] **Step 4: Add planner tests for pending per-job choices**

```python
def test_job_starts_with_independent_image_and_preview_choices(self):
    plan = build_job_plan(SCRIPT, _registry(), {})

    self.assertEqual("pending", plan["task"]["image_generation_choice"])
    self.assertEqual("pending", plan["task"]["selected_image_source"])
    self.assertEqual("pending", plan["task"]["preview_choice"])
    self.assertEqual("image1", plan["visual_plan"]["identity_master_alias"])
```

Implement the two task fields in `build_job_plan` without changing the exact script or duration fields.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_directors.VisualDirectorTests tests.test_planner.PlannerTests -v
```

Expected: PASS.

Commit:

```powershell
git add scripts/dhflow/visual_director.py scripts/dhflow/planner.py tests/test_directors.py tests/test_planner.py
git commit -m "feat: plan approved per-job avatar looks"
```

### Task 2: Add image-choice and exact image-approval state gates

**Files:**
- Modify: `scripts/dhflow/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write failing state tests**

Add tests for the two branches and approval binding:

```python
def test_no_new_image_selects_original_image1(self):
    state = create_state(status="planned")
    choice = record_image_choice(state, generate_new=False)
    self.assertEqual("image_generation_choice_recorded", choice["status"])
    chosen = record_original_image_selection(choice)

    self.assertEqual("image_approved", chosen["status"])
    self.assertEqual("original_image1", chosen["assets"]["job_image"]["source"])
    self.assertEqual("image1", chosen["assets"]["job_image"]["identity_master_alias"])


def test_new_image_requires_candidate_and_bound_approval(self):
    choice = record_image_choice(create_state(status="planned"), generate_new=True)
    state = start_image_generation(choice)
    self.assertEqual("awaiting_image_approval", state["status"])

    with self.assertRaisesRegex(ValueError, "candidate image"):
        record_image_approval(
            state,
            reviewer="user",
            recorded_at="2026-08-07T12:00:00+08:00",
            evidence_ref="conversation-message-image-1",
        )


def test_image_approval_binds_candidate_sha256_and_reference(self):
    choice = record_image_choice(create_state(status="planned"), generate_new=True)
    state = start_image_generation(choice)
    state = record_image_candidate(
        state,
        content_sha256="a" * 64,
        artifact_ref="work/jobs/job-1/candidate.png",
    )
    approved = record_image_approval(
        state,
        reviewer="user",
        recorded_at="2026-08-07T12:00:00+08:00",
        evidence_ref="conversation-message-image-1",
    )

    self.assertEqual("image_approved", approved["status"])
    self.assertEqual("a" * 64, approved["approval"]["image_candidate_sha256"])
```

- [ ] **Step 2: Run the tests and observe failure**

Run:

```powershell
python -m unittest tests.test_state -v
```

Expected: FAIL because the v3 statuses and record functions do not exist.

- [ ] **Step 3: Upgrade the state schema and implement the image branch**

Set schema version 3 and use this ordered state list:

```python
STATES = (
    "created",
    "planned",
    "image_generation_choice_recorded",
    "awaiting_image_approval",
    "image_approved",
    "preview_choice_recorded",
    "preview_rendering",
    "awaiting_preview_approval",
    "full_raw_rendering",
    "raw_qa",
    "awaiting_raw_approval",
    "post_production",
    "final_qa",
    "complete",
)
```

Add `image` and `preview` approval fields while preserving strict raw approval:

```python
"approval": {
    "image": False,
    "preview": False,
    "raw": False,
}
```

Implement the exact public functions `record_image_choice(state, *, generate_new)`, `record_original_image_selection(state)`, `start_image_generation(state)`, `record_image_candidate(state, *, content_sha256, artifact_ref)`, and `record_image_approval(state, *, reviewer, recorded_at, evidence_ref)` using `deepcopy`, the existing strict SHA-256/reference validators, and the transition rules below.

Requirements:

- `record_image_choice` always records the explicit answer and advances exactly one step to `image_generation_choice_recorded`.
- `record_original_image_selection` is valid only for `generate_new=False`; it records the original `image1` source and advances to `image_approved` without fabricating user approval evidence.
- `start_image_generation` is valid only for `generate_new=True`; it advances to `awaiting_image_approval` with no approval authority.
- Candidate recording is idempotent for the same hash/reference and rejects conflicts.
- Approval binds reviewer, RFC 3339 timestamp, stable evidence reference, candidate SHA-256, and artifact reference.
- Image approval never changes preview or raw approval.

- [ ] **Step 4: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_state -v
```

Expected: image-gate tests PASS; legacy tests may still fail on expected version/status changes and are addressed in Tasks 3 and 5.

Commit:

```powershell
git add scripts/dhflow/state.py tests/test_state.py
git commit -m "feat: gate jobs on exact image approval"
```

### Task 3: Add preview approval and truthful render-evidence recording

**Files:**
- Modify: `scripts/dhflow/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write failing tests for preview and render evidence**

```python
def test_preview_choice_is_per_job_and_requires_image_approval(self):
    choice = record_image_choice(create_state(status="planned"), generate_new=False)
    state = record_original_image_selection(choice)
    preview = record_preview_choice(state, enabled=True)
    self.assertEqual("preview_choice_recorded", preview["status"])
    self.assertTrue(preview["providers"]["heygen"]["preview_requested"])


def test_blueprint_evidence_cannot_start_rendering(self):
    state = record_preview_choice(
        record_original_image_selection(
            record_image_choice(create_state(status="planned"), generate_new=False)
        ),
        enabled=True,
    )
    with self.assertRaisesRegex(ValueError, "real render evidence"):
        record_render_started(
            state,
            kind="preview",
            evidence={
                "session_status": "thinking",
                "progress": 0,
                "video_count": 0,
                "generate_button_visible": True,
                "avatar_bound": False,
                "resource_type": "blueprint",
            },
        )


def test_real_preview_render_requires_stable_video_id(self):
    state = record_preview_choice(
        record_original_image_selection(
            record_image_choice(create_state(status="planned"), generate_new=False)
        ),
        enabled=True,
    )
    rendering = record_render_started(
        state,
        kind="preview",
        video_id="preview-video-1",
        evidence={
            "session_status": "generating",
            "progress": 1,
            "video_count": 1,
            "generate_button_visible": False,
            "avatar_bound": True,
            "resource_type": "video",
        },
    )
    self.assertEqual("preview_rendering", rendering["status"])
```

- [ ] **Step 2: Run tests and observe failure**

Run:

```powershell
python -m unittest tests.test_state -v
```

Expected: FAIL because preview and render-evidence functions are missing.

- [ ] **Step 3: Implement explicit preview and render functions**

Add the exact public functions `record_preview_choice(state, *, enabled)`, `record_render_started(state, *, kind, evidence, video_id=None)`, `record_preview_result(state, *, video_id, content_sha256, artifact_ref, qa_passed)`, and `record_preview_approval(state, *, reviewer, recorded_at, evidence_ref)` using the same idempotent copy-and-validate pattern as `record_raw_video` and `record_raw_approval`.

Validation rules:

- Replace the linear index-only transition rule with an explicit adjacency map so the no-image and no-preview branches are legal without allowing arbitrary skips:

```python
ALLOWED_TRANSITIONS = {
    "planned": {"image_generation_choice_recorded"},
    "image_generation_choice_recorded": {
        "awaiting_image_approval",
        "image_approved",
    },
    "awaiting_image_approval": {"image_approved"},
    "image_approved": {"preview_choice_recorded"},
    "preview_choice_recorded": {"preview_rendering", "full_raw_rendering"},
    "preview_rendering": {"awaiting_preview_approval"},
    "awaiting_preview_approval": {"full_raw_rendering"},
    "full_raw_rendering": {"raw_qa"},
    "raw_qa": {"awaiting_raw_approval"},
    "awaiting_raw_approval": {"post_production"},
    "post_production": {"final_qa"},
    "final_qa": {"complete"},
}
```

- Preview choice only follows `image_approved`.
- When preview is disabled, full raw becomes the next render kind.
- `thinking/progress=0`, blueprint/draft resources, empty video lists, visible Generate buttons, or unbound avatars never qualify as real rendering.
- `video_id` is mandatory before entering either render state.
- Preview approval binds the exact preview video ID and SHA-256, but never authorizes post-production.
- Full raw submission requires preview approval when preview was requested.

- [ ] **Step 4: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_state -v
```

Expected: PASS for image, preview, render, and raw-boundary tests.

Commit:

```powershell
git add scripts/dhflow/state.py tests/test_state.py
git commit -m "feat: verify real HeyGen render state"
```

### Task 4: Replace the active API-credit action plan with a browser submission plan

**Files:**
- Create: `scripts/dhflow/heygen_web.py`
- Modify: `scripts/dhflow/planner.py`
- Modify: `scripts/plan_job.py`
- Create: `tests/test_heygen_web.py`
- Modify: `tests/test_planner.py`

- [ ] **Step 1: Write failing browser-plan tests**

Create `tests/test_heygen_web.py` with:

```python
import unittest

from scripts.dhflow.heygen_web import (
    build_web_submission_plan,
    classify_render_evidence,
)

VOICE_PLAN = {
    "persona": "professional",
    "segments": [
        {
            "id": "beat-1",
            "text": "企业培训必须从真实业务开始。",
            "role": "conclusion",
            "delivery": {
                "speed": "measured",
                "emotion": "confident",
                "pause_before": None,
                "pause_after": None,
                "emphasis": "action",
            },
        }
    ],
}
VISUAL_PLAN = {
    "identity_alias": "image1",
    "identity_master_alias": "image1",
    "identity_invariants": {"recognizability": "preserve"},
    "hand_topology": "separated",
    "wardrobe": "business_casual",
    "background": "quiet_professional_interior",
    "framing": "medium_shot",
    "pose": {"neutral_ready": True, "hands_separated": True},
    "mouth_visibility": "unobstructed",
    "safe_areas": {"head_motion_space": "clear"},
    "camera": {"locked": True},
    "image_qa_requirements": ["identity_consistency"],
    "job_look": {
        "generation_choice": "pending",
        "candidate_count": 1,
        "explicit_approval_required": True,
        "fallback": "original_image1",
        "retention": "same_identity_group",
        "selected_source": "pending",
    },
    "aspect_ratio": "9:16",
    "resolution": "720p",
}
PERFORMANCE_PLAN = {
    "profile": "natural_business",
    "hand_topology": "separated",
    "beats": [
        {
            "id": "beat-1",
            "text": "企业培训必须从真实业务开始。",
            "role": "conclusion",
            "face": {"enabled": True, "action": "micro_emphasis", "intensity": "low"},
            "head": {
                "enabled": True,
                "action": "small_nod",
                "intensity": "low",
                "returns_to_center": True,
            },
            "hands": {
                "enabled": True,
                "intensity": "low",
                "main_action": "open_palm",
                "cycle": {
                    "prepare": True,
                    "stroke": True,
                    "optional_hold": False,
                    "retract": True,
                    "cooldown": True,
                },
                "anchor_hand": True,
            },
            "body": {
                "enabled": True,
                "action": "stable_breathing",
                "intensity": "low",
                "torso_stable": True,
            },
        }
    ],
}


class HeyGenWebPlanTests(unittest.TestCase):
    def test_plan_binds_exact_assets_script_settings_and_motion(self):
        plan = build_web_submission_plan(
            script="企业培训必须从真实业务开始。",
            voice_plan=VOICE_PLAN,
            visual_plan=VISUAL_PLAN,
            performance_plan=PERFORMANCE_PLAN,
            voice_id="voice-1",
            avatar_group_id="group-1",
        )

        self.assertEqual("heygen-web-plan-credits", plan["transport"])
        self.assertEqual("企业培训必须从真实业务开始。", plan["preSubmit"]["exactScript"])
        self.assertEqual("voice-1", plan["preSubmit"]["requiredVoiceId"])
        self.assertEqual("9:16", plan["preSubmit"]["aspectRatio"])
        self.assertEqual("720p", plan["preSubmit"]["resolution"])
        self.assertEqual("avatar_iv", plan["preSubmit"]["engine"])
        self.assertTrue(plan["preSubmit"]["motionPrompt"])
        self.assertNotIn("mcp__codex_apps__heygen_create_speech", str(plan))
        self.assertNotIn("mcp__codex_apps__heygen_create_video_from_avatar", str(plan))

    def test_blueprint_is_not_rendering(self):
        self.assertEqual(
            "blueprint_ready",
            classify_render_evidence(
                session_status="thinking",
                progress=0,
                video_count=0,
                generate_button_visible=True,
                avatar_bound=False,
                resource_type="blueprint",
            ),
        )

    def test_generating_requires_bound_avatar_and_real_video(self):
        self.assertEqual(
            "rendering",
            classify_render_evidence(
                session_status="generating",
                progress=5,
                video_count=1,
                generate_button_visible=False,
                avatar_bound=True,
                resource_type="video",
            ),
        )
```

- [ ] **Step 2: Run tests and observe failure**

Run:

```powershell
python -m unittest tests.test_heygen_web -v
```

Expected: FAIL because `scripts.dhflow.heygen_web` does not exist.

- [ ] **Step 3: Implement the browser plan and evidence classifier**

Implement `build_web_submission_plan(*, script, voice_plan, visual_plan, performance_plan, voice_id, avatar_group_id)` and `classify_render_evidence(*, session_status, progress, video_count, generate_button_visible, avatar_bound, resource_type)` as the only public functions in `heygen_web.py`.

The plan action order must be:

```python
[
    "openLoggedInHeyGen",
    "selectOrUploadApprovedLook",
    "bindExactVoice",
    "enterExactScript",
    "setAvatarIvPortrait720p",
    "disableExtras",
    "applyMotionPrompt",
    "verifyBeforeSpend",
    "clickGenerate",
    "verifyRealRender",
    "pollExistingVideo",
]
```

The pre-submit guard must reject empty avatar binding, voice-ID mismatch, rewritten script, duration mismatch, missing motion prompt, captions/music/B-roll enabled, camera motion, wrong orientation/resolution/engine, or more than one candidate image.

The evidence classifier returns only `blueprint_ready`, `blocked`, `rendering`, or `completed`; it never trusts a success message string.

- [ ] **Step 4: Switch the planner to the browser plan**

Replace:

```python
from scripts.dhflow.heygen_app import build_app_action_plan
```

with:

```python
from scripts.dhflow.heygen_web import build_web_submission_plan
```

Pass the exact original script into the new builder. Keep the JSON output key and filename `heygen_app_plan` / `heygen-app-plan.json` so existing job directories remain compatible, but set its internal transport to `heygen-web-plan-credits`.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_heygen_web tests.test_planner -v
```

Expected: PASS and no serialized plan contains either API-credit creation tool.

Commit:

```powershell
git add scripts/dhflow/heygen_web.py scripts/dhflow/planner.py scripts/plan_job.py tests/test_heygen_web.py tests/test_planner.py
git commit -m "feat: plan HeyGen web-credit submissions"
```

### Task 5: Add CLI events and safe v2-to-v3 migration

**Files:**
- Modify: `scripts/update_job_state.py`
- Modify: `scripts/migrate_job_state.py`
- Modify: `scripts/dhflow/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write failing CLI and migration tests**

Add CLI cases for:

```text
image-choice --generate-new
image-choice --use-original
image-candidate --sha256 <hash> --artifact-ref <path>
approve-image --reviewer <name> --recorded-at <rfc3339> --evidence-ref <ref>
preview-choice --enabled
preview-choice --disabled
render-started --kind preview|full_raw --video-id <id> --evidence-json <path>
preview-result --video-id <id> --sha256 <hash> --artifact-ref <path> --qa-passed
approve-preview --reviewer <name> --recorded-at <rfc3339> --evidence-ref <ref>
```

Add a migration test asserting that a valid v2 `planned` state becomes v3 `planned`, and a later v2 state is conservatively mapped without inheriting preview/image authority:

```python
def create_v2_fixture(status):
    return {
        "version": 2,
        "status": status,
        "approval": {"raw": False},
        "providers": {},
        "assets": {},
        "artifacts": {},
        "error": {},
        "retry": {},
    }


def test_v2_migration_requires_new_image_and_preview_decisions(self):
    old = create_v2_fixture(status="assets_ready")
    migrated = migrate_v2(old)

    self.assertEqual(3, migrated["version"])
    self.assertEqual("planned", migrated["status"])
    self.assertFalse(migrated["approval"]["image"])
    self.assertFalse(migrated["approval"]["preview"])
    self.assertFalse(migrated["approval"]["raw"])
```

- [ ] **Step 2: Run tests and observe failure**

Run:

```powershell
python -m unittest tests.test_state.UpdateStateCliTests tests.test_state.StateMigrationTests -v
```

Expected: FAIL because the events and v2 migration do not exist.

- [ ] **Step 3: Implement CLI parsing and dispatch**

Import and dispatch each new state function in `update_job_state.py`. Read render evidence from a local strict-JSON file and reject URLs, credentials, unknown fields, NaN, or non-object JSON.

Keep atomic write, backup, and compare-before-replace behavior unchanged.

- [ ] **Step 4: Implement conservative v2 migration**

Add `migrate_v2` in `state.py` and route version 2 in `migrate_job_state.py`.

Rules:

- Preserve stable voice/avatar IDs and local artifact fingerprints when schema-valid.
- Never preserve temporary URLs or raw provider payloads.
- Never infer image or preview approval from old statuses.
- Never preserve raw approval unless it is already bound to a matching QA-passed full raw hash and HeyGen video ID; otherwise reset it.
- Map ambiguous in-progress v2 jobs back to v3 `planned` so the new per-job image and preview questions are asked.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_state -v
```

Expected: PASS.

Commit:

```powershell
git add scripts/dhflow/state.py scripts/update_job_state.py scripts/migrate_job_state.py tests/test_state.py
git commit -m "feat: persist variable-look workflow state"
```

### Task 6: Add a strict sequential batch queue

**Files:**
- Create: `scripts/dhflow/queue.py`
- Create: `scripts/queue_jobs.py`
- Create: `tests/test_queue.py`

- [ ] **Step 1: Write failing queue tests**

Create `tests/test_queue.py`:

```python
import unittest

from scripts.dhflow.queue import create_queue, next_actionable_job, validate_queue


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

    def test_queue_rejects_duplicate_or_unknown_job_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate job ID"):
            create_queue(["job-1", "job-1"])
        with self.assertRaisesRegex(ValueError, "job ID"):
            validate_queue({"version": 1, "job_ids": [True]})
```

- [ ] **Step 2: Run tests and observe failure**

Run:

```powershell
python -m unittest tests.test_queue -v
```

Expected: FAIL because the queue module does not exist.

- [ ] **Step 3: Implement the minimal FIFO queue**

Implement these three public functions using the constants and rules below: `create_queue(job_ids)`, `validate_queue(queue)`, and `next_actionable_job(queue, job_statuses)`.

```python
BLOCKING_APPROVAL_STATES = frozenset(
    {
        "awaiting_image_approval",
        "awaiting_preview_approval",
        "awaiting_raw_approval",
    }
)
```

The queue is strict JSON:

```json
{"version": 1, "job_ids": ["job-1", "job-2"]}
```

Rules:

- preserve user input order;
- reject empty, malformed, duplicate, URL-like, or credential-like job IDs;
- return no actionable job when the queue head waits for any user approval;
- skip completed jobs and return the first remaining planned/resumable head;
- never execute two jobs concurrently.

- [ ] **Step 4: Add the local queue CLI**

`scripts/queue_jobs.py` supports:

```text
create <queue.json> <job-id-1> <job-id-2>
next <queue.json> --states-dir <jobs-root>
```

Use the same atomic write/backup approach as `update_job_state.py`. `next` prints either the single actionable job ID or `blocked`; it performs no image, browser, HeyGen, or HyperFrames actions.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_queue -v
```

Expected: PASS.

Commit:

```powershell
git add scripts/dhflow/queue.py scripts/queue_jobs.py tests/test_queue.py
git commit -m "feat: queue digital human jobs sequentially"
```

### Task 7: Rewrite the Skill runtime contract and checklists

**Files:**
- Modify: `SKILL.md`
- Modify: `references/framework.md`
- Modify: `references/checklists.md`
- Modify: `references/api-facts.md`
- Create: `references/browser-submission.md`
- Modify: `agents/openai.yaml`
- Create: `tests/test_skill_contract.py`

- [ ] **Step 1: Write failing contract tests**

Create `tests/test_skill_contract.py`:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_requires_per_job_image_question_and_exact_adoption(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("是否调用内置生图模型生成新的老板形象", text)
        self.assertIn("明确回复“采用”", text)
        self.assertIn("原始图片1", text)

    def test_active_contract_forbids_api_credit_creation_tools(self):
        active = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "SKILL.md",
                "references/framework.md",
                "references/checklists.md",
                "references/api-facts.md",
                "references/browser-submission.md",
            )
        )
        self.assertNotIn("mcp__codex_apps__heygen_create_speech", active)
        self.assertNotIn("mcp__codex_apps__heygen_create_video_from_avatar", active)

    def test_skill_defines_truthful_generation_evidence(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for required in (
            "thinking",
            "progress=0",
            "blueprint",
            "生成按钮",
            "不得报告“正在生成”",
        ):
            self.assertIn(required, text)
```

- [ ] **Step 2: Run tests and observe failure**

Run:

```powershell
python -m unittest tests.test_skill_contract -v
```

Expected: FAIL because the current Skill still documents direct App speech/video actions and lacks the new gates.

- [ ] **Step 3: Update `SKILL.md`**

Replace the required order with the approved workflow:

1. Rights/account/registry/preflight.
2. Plan exact script and identity invariants.
3. Ask the per-job new-image question.
4. Use original image1 on “no”; on “yes” generate exactly one built-in-model candidate.
5. Stop for exact candidate approval; only the word-level evidence tied to the candidate artifact authorizes upload.
6. Retain every approved look in the same identity group with a task-derived name.
7. Ask the per-job 15-second preview question.
8. Drive the logged-in HeyGen web page to bind exact image, voice1, verbatim script, Avatar IV, 9:16, 720P, and the complete motion prompt.
9. Verify all pre-spend fields, click Generate, then verify real render evidence.
10. Preview/full-raw/HyperFrames approval boundaries remain separate.

Explicitly forbid claiming generation from blueprints, `thinking/progress=0`, empty video lists, visible Generate buttons, blank avatar selectors, or connector success text.

- [ ] **Step 4: Update references and UI metadata**

`references/browser-submission.md` must instruct the runtime agent to:

- use accessibility roles and visible labels rather than hard-coded CSS selectors;
- select or upload the exact approved look and verify its thumbnail is visible;
- verify the exact stable voice identity, not only a duplicated display name;
- paste the exact script and compare normalized visible text before spend;
- set Avatar IV, portrait 9:16, 720P, no captions/music/B-roll;
- preserve and verify the full motion block;
- click Generate once;
- capture post-click page state and classify it with the v3 evidence rules;
- stop with a precise blocker when the page cannot be safely controlled.

Update `agents/openai.yaml` default prompt to mention the image question, one generated candidate, exact “采用” approval, original-image fallback, plan-credit web submission, and verified real rendering.

- [ ] **Step 5: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_skill_contract -v
```

Expected: PASS.

Commit:

```powershell
git add SKILL.md references/framework.md references/checklists.md references/api-facts.md references/browser-submission.md agents/openai.yaml tests/test_skill_contract.py
git commit -m "docs: enforce variable-look web production"
```

### Task 8: Remove obsolete active API-credit planning and verify the complete suite

**Files:**
- Delete: `scripts/dhflow/heygen_app.py`
- Delete: `tests/test_heygen_app.py`
- Modify: `README.md`
- Test: all files under `tests/`

- [ ] **Step 1: Prove no production import depends on the obsolete module**

Run:

```powershell
rg -n "heygen_app|build_app_action_plan|create_speech|create_video_from_avatar" scripts tests SKILL.md references agents README.md
```

Expected before deletion: matches only in the obsolete module/tests and documentation that Task 6 replaces. Any production import is a blocker and must be changed to `heygen_web` before continuing.

- [ ] **Step 2: Delete the obsolete module and its obsolete tests**

Remove `scripts/dhflow/heygen_app.py` and `tests/test_heygen_app.py` only after Step 1 proves nothing active imports them.

Update `README.md` to describe the identity-master/per-job-look model and logged-in browser submission without adding installation or API-key instructions.

- [ ] **Step 3: Run the complete test suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: all tests PASS with no skipped variable-look, approval, browser-plan, or render-evidence tests.

- [ ] **Step 4: Run static repository checks**

Run:

```powershell
git diff --check
rg -n "mcp__codex_apps__heygen_create_speech|mcp__codex_apps__heygen_create_video_from_avatar|requiresPlanCredits.*create" SKILL.md references scripts agents
```

Expected: all commands produce no prohibited matches and `git diff --check` exits 0.

- [ ] **Step 5: Run one local dry-run fixture**

Use the existing authorized registry fixture and a 15–90 second script:

```powershell
python scripts/plan_job.py `
  --script tests/fixtures/steps-cta.md `
  --registry tests/fixtures/registry.json `
  --output-dir work/verification-variable-look `
  --dry-run
```

If the repository has no committed `registry.json` fixture, create the temporary strict-JSON registry under `work/verification-variable-look/registry.json` from the same values used by `tests/test_planner.py`; do not commit provider credentials or temporary URLs.

Verify:

- exactly seven job JSON artifacts are written;
- `task.json` has pending image and preview choices;
- `visual-plan.json` has the immutable master and one-candidate approval contract;
- `heygen-app-plan.json` uses `heygen-web-plan-credits` and has no API-credit creation tools;
- `state.json` is valid v3 at `planned`.

- [ ] **Step 6: Commit the cleanup**

```powershell
git add -A scripts/dhflow/heygen_app.py tests/test_heygen_app.py README.md
git commit -m "refactor: retire API-credit production plan"
```

### Task 9: Sync and validate the installed Skill

**Files:**
- Source: repository files changed by Tasks 1–8
- Destination: `C:\Users\78575\.codex\skills\rachel-digital-human-production\`

- [ ] **Step 1: Verify the source worktree is clean**

Run:

```powershell
git status --short
git log -8 --oneline
```

Expected: clean status and one intentional commit per implementation task.

- [ ] **Step 2: Copy only the production Skill payload**

Copy `SKILL.md`, `agents/`, `references/`, and `scripts/` from the feature worktree to the installed Skill directory. Do not copy `.git`, `.worktrees`, `docs`, `tests`, `README.md`, `LICENSE`, caches, job outputs, credentials, or temporary URLs.

Before replacing files, compare source and destination paths. Delete only obsolete installed files explicitly removed by this plan (`scripts/dhflow/heygen_app.py` and matching `__pycache__` entry); do not recursively clear the installed Skill directory.

- [ ] **Step 3: Run tests against the installed copy**

Run the repository tests with imports redirected to the installed Skill root, or run an equivalent smoke test that imports:

```python
from scripts.dhflow.heygen_web import build_web_submission_plan
from scripts.dhflow.state import (
    create_state,
    record_image_choice,
    record_original_image_selection,
)
```

Expected: imports succeed and the installed `SKILL.md` contains the new-image question, exact “采用” gate, browser submission rule, complete motion block, and truthful generation evidence rules.

- [ ] **Step 4: Final verification report**

Report:

- source commit IDs;
- full test command and pass count;
- installed Skill path;
- confirmation that no live HeyGen or image generation was triggered during implementation tests;
- confirmation that the next real job will first ask whether to generate a new boss image.
