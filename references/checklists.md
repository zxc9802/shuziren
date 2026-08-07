# Production Checklists

Use each checklist at its named gate. A later gate never substitutes for an earlier one.

## Authorization and planning

- [ ] Confirm rights to `voice1`, `image1`, the script, intended use, and distribution.
- [ ] Confirm the logged-in HeyGen paid account and 网页套餐额度; do not request an API key.
- [ ] Resolve authorized registry records and verify local source SHA-256 values.
- [ ] Run preflight and `scripts/plan_job.py --dry-run`; parse all seven JSON artifacts.
- [ ] Confirm exact script preservation and estimated duration of 15-90 seconds.

## Per-job image decision

- [ ] Ask “这个任务是否调用内置生图模型生成新的老板形象？” for this job.
- [ ] On no, select 原始图片1 and record `original_image1`.
- [ ] On yes, generate exactly one candidate with `image1` identity preserved.
- [ ] Check face, age, skin tone, hair, eyewear, body type, hands, mouth, crop, and recognizability.
- [ ] Display the candidate and stop until the user明确回复“采用” for that artifact.
- [ ] Bind approval to candidate SHA-256 and stable reference; do not accept generic continuation.
- [ ] Retain the adopted look in the same identity group with a task-derived name.

## Per-job preview decision

- [ ] Ask whether this job needs a 15-second low-cost preview only after the image is selected.
- [ ] Record explicit yes/no; never reuse a previous job answer.
- [ ] If yes, require approval of the exact preview before full-raw submission.
- [ ] If no, proceed directly to the full raw after all browser pre-spend checks.

## HeyGen browser pre-spend

- [ ] Read `references/browser-submission.md`.
- [ ] Use the logged-in web app and 网页套餐额度, not API credits.
- [ ] Select/upload the exact approved look and verify its thumbnail is visibly bound.
- [ ] Bind the exact stable `voice1` identity.
- [ ] Paste the verbatim script and compare visible normalized text with the source.
- [ ] Set Avatar IV, portrait `9:16`, `720P`, locked camera.
- [ ] Disable captions, music, B-roll, transitions, and camera motion.
- [ ] Preserve the full semantic voice direction and motion prompt.
- [ ] Confirm one candidate maximum and complete-script duration; reject truncation or unexpected silence.
- [ ] Do not ask the user to select the avatar/voice or click Generate.
- [ ] Click Generate once only after every field passes.

## Real-render evidence

- [ ] Capture the page immediately after the click.
- [ ] Require a stable video ID, bound avatar, video resource, nonzero progress, and nonempty video list.
- [ ] Require the Generate button to be absent/disabled for the submitted job.
- [ ] Classify `thinking + progress=0`, blueprint/draft, empty videos, visible Generate, or blank avatar as not rendering.
- [ ] Do not trust a connector/chat “success” sentence as evidence.
- [ ] Poll the existing video ID; never click Generate again because polling is slow.

## Motion, voice, and full-file QA

- [ ] Verify speed, pauses, emphasis, and emotion vary by semantic beat.
- [ ] Verify fixed camera and framing: no pan, zoom, tilt, crop jump, cuts, or shake.
- [ ] Verify direct gaze, irregular blinks, subtle expressions, calm breathing, stable torso.
- [ ] Verify phrase-led head movement returns to center.
- [ ] Verify each visible-hand gesture completes prepare, stroke, retract, cooldown, then neutral.
- [ ] Reject pendulum motion, repetitive gestures, mechanical synchrony, fused anatomy, or invented limbs.
- [ ] Decode the complete media; verify duration, audio, lip sync, first/last word, and first/last frame.
- [ ] Record stable video ID, exact artifact SHA-256/reference, and strict QA result.

## Exact approvals and HyperFrames

- [ ] Deliver the named preview/raw artifact and stop at its approval state.
- [ ] Bind approval only to the exact artifact the user explicitly approved.
- [ ] Keep image, preview, and raw approvals separate.
- [ ] Do not substitute rights consent, spending consent, automatic QA, silence, or an earlier “继续”.
- [ ] Start HyperFrames only after bound full-raw approval permits `post_production`.
- [ ] Use the approved raw unchanged as the base; preserve identity, lip sync, voice, and performance.
- [ ] Run HyperFrames lint, validation, inspection, preview, and render QA.

## Batch and archive

- [ ] Use the strict FIFO queue; never run two jobs concurrently.
- [ ] Stop all later jobs while the head waits for image, preview, or raw approval.
- [ ] Archive script, seven plans, state v3, approved look, stable IDs, hashes, QA, evidence, raw/final media, and retry notes.
- [ ] Confirm no credentials, headers, temporary URLs, or embedded private media are stored.
- [ ] Mark `complete` only after final-file QA passes.
