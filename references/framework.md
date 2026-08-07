# Modular Digital Human Framework

## Identity and job looks

The registry is the trust boundary. `voice1` is the stable HeyGen cloned voice and `image1` is the boss identity master. Store only authorized local fingerprints and stable remote IDs; never store credentials, headers, temporary URLs, or raw provider payloads.

Every job begins with two independent pending choices:

1. whether to generate one new boss-look candidate;
2. whether to generate a 15-second preview.

Ask the image question first. A no answer selects `original_image1`. A yes answer creates exactly one built-in-model candidate. Preserve identity invariants while allowing wardrobe, pose, background, lighting, framing, and props to vary. The candidate cannot become the selected job image until the user explicitly says “采用” for that exact artifact. Retain adopted looks in the same identity group with task-derived names; never overwrite `image1`.

## Seven planning artifacts

`scripts/plan_job.py --dry-run` performs no network calls and atomically creates:

1. `task.json`: exact script, duration, aliases, pending image/preview choices, settings, overrides.
2. `content-beats.json`: character-preserving semantic beats.
3. `voice-plan.json`: per-beat speed, pause, emphasis, and emotion.
4. `visual-plan.json`: identity master, job-look policy, scene, framing, pose, topology, QA.
5. `performance-plan.json`: face, head, hand, and body behavior with complete gesture cycles.
6. `heygen-app-plan.json`: backward-compatible filename containing the `heygen-web-plan-credits` browser action plan.
7. `state.json`: v3 state at `planned`, with image/preview/raw approvals false.

Planning is valid only for estimated 15-90 second scripts and preserves the submitted text exactly.

## Paid-plan browser transport

Live generation uses the logged-in HeyGen web account and 网页套餐额度. Do not use API creation tools, provider HTTP, provider CLI, or another voice service.

Execute the browser plan in this order:

```text
open logged-in HeyGen
-> select or upload exact approved look
-> bind exact voice1
-> enter verbatim script
-> set Avatar IV, 9:16, 720P
-> disable captions, music, B-roll, camera motion
-> preserve the complete motion prompt
-> verify every visible pre-spend field
-> click Generate once
-> verify real render evidence
-> poll the existing stable video ID
```

The runtime controls the page. It must not ask the user to manually select the avatar or voice, click Generate, or repeat setup already represented by stable assets. If the page cannot be controlled or the private look cannot be bound, stop with the exact blocker.

## State v3 and explicit events

The authoritative stages are:

```text
created
-> planned
-> image_generation_choice_recorded
-> awaiting_image_approval | image_approved
-> image_approved
-> preview_choice_recorded
-> preview_rendering | full_raw_rendering
-> awaiting_preview_approval | raw_qa
-> full_raw_rendering
-> raw_qa
-> awaiting_raw_approval
-> post_production
-> final_qa
-> complete
```

Use `scripts/update_job_state.py` events:

- `image-choice --generate-new|--use-original`
- `image-candidate --sha256 ... --artifact-ref ...`
- `approve-image --reviewer ... --recorded-at ... --evidence-ref ...`
- `preview-choice --enabled|--disabled`
- `render-started --kind preview|full_raw --video-id ... --evidence-json ...`
- `preview-result ... --qa-passed|--qa-failed`
- `approve-preview ...`
- `raw-video ... --qa-passed|--qa-failed`
- `approve-raw ...`

Identical events are idempotent; conflicting artifacts or evidence fail. Each approval binds the exact relevant ID, SHA-256, stable artifact reference, reviewer, timestamp, and evidence reference. Original-image selection reaches `image_approved` without fabricating user approval evidence.

## Truth boundary

`thinking/progress=0`, blueprint/draft resources, zero videos, a visible Generate button, an unbound avatar, or connector success text never enters a rendering state. `render-started` requires observable real-video evidence and a stable video ID. Slow polling reuses that ID; it never causes a second paid submission.

## Strict FIFO batches

Queue files are strict JSON: `{"version":1,"job_ids":[...]}`. `scripts/queue_jobs.py next` returns only the first actionable job or `blocked`. Completed heads are skipped. Any head at `awaiting_image_approval`, `awaiting_preview_approval`, or `awaiting_raw_approval` blocks every later job. Never run two jobs concurrently.

## Approval boundaries

- Image approval selects only the generated look.
- Preview approval permits only full-raw generation.
- Raw approval permits only the transition to post-production.
- HyperFrames may start only after `post_production` validates the bound full-raw approval.

Rights confirmation, account authorization, credit-spend consent, automatic QA, silence, “继续”, or approval of another artifact cannot substitute.

## Recovery and migration

- Inspect state before each live action and persist stable evidence immediately.
- Reuse complete voice/identity assets and approved looks; do not clone or upload duplicates.
- Continue polling the existing video ID after timeout.
- Fetch a result again after a temporary download URL expires; do not rerender.
- Migrate v1/v2 conservatively. Ambiguous old jobs return to `planned` and must answer the image and preview questions again.
- Preserve only schema-valid stable IDs and local fingerprints. Never infer image/preview authority from old statuses.
