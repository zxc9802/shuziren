---
name: rachel-digital-human-production
description: Use when the user invokes 数字人skill or asks to produce or batch-automate authorized 15-90 second Chinese HeyGen digital-human talking-head videos with a stable cloned voice and boss identity, variable per-job looks, optional previews, natural semantic motion, exact artifact approvals, or HyperFrames packaging.
---

# 数字人skill

## Core contract

Use the logged-in HeyGen web account and its 网页套餐额度 for live generation. Do not request an API key, call provider HTTP, use API credits, or switch to another voice service.

Keep these long-term assets stable:

- `voice1`: the same authorized cloned voice. Vary speed, pauses, emphasis, and emotion by script semantics; never read the whole script at one constant speed.
- `image1`: the identity master. Preserve face shape, features, apparent age, skin tone, hairstyle, eyewear, body type, and recognizability.
- 原始图片1: the default per-job look when the user declines a new image.

Wardrobe, pose, background, lighting, framing, and props may vary by job. Identity may not.

## Required job order

Execute every job in this order. Each decision belongs only to the current job.

1. Confirm authorization for the voice, portrait, script, use, and distribution. Confirm the logged-in paid HeyGen account before spending 网页套餐额度.
2. Resolve `voice1` and `image1`, preserve the submitted script exactly, and run local planning. Duration must be 15-90 seconds; otherwise present a rewrite and wait for approval.
3. Ask exactly: **“这个任务是否调用内置生图模型生成新的老板形象？”** Do this for 每个任务, even when a previous task used a generated look.
4. If the answer is no, select 原始图片1 and record `original_image1`. If yes, use the built-in image model to generate exactly one candidate that preserves `image1` identity while adapting clothing, pose, background, lighting, and framing to the script.
5. Display that exact candidate and stop. Continue only after the user explicitly and 明确回复“采用” for that image. Bind approval to its SHA-256 and artifact reference. “可以”, “继续”, silence, earlier authorization, or approval of another image does not count.
6. Retain every adopted look under the same boss identity group with a task-derived name. Never replace the `image1` identity master.
7. Ask: **“这个任务需要先生成15秒低成本预览吗？”** Record an explicit yes/no for this job. Do not reuse an earlier answer.
8. Read `references/browser-submission.md`. Drive the logged-in HeyGen page yourself: 自动绑定 the adopted image or 原始图片1, exact `voice1`, verbatim script, Avatar IV, portrait `9:16`, `720P`, disabled captions/music/B-roll, locked camera, and the complete motion prompt. 不得要求用户手动选择 avatar/voice or click Generate.
9. Re-read all visible pre-spend fields. Reject blank avatar binding, voice mismatch, rewritten/truncated script, duration mismatch, missing motion prompt, wrong engine/orientation/resolution, enabled extras, camera motion, or more than one candidate. Then 点击一次生成.
10. Capture the post-click page state. Do not infer execution from a success sentence. A 稳定 video ID, bound avatar, video resource, nonzero progress, hidden Generate button, and real video count are required before reporting generation.
11. If preview was selected, deliver the exact 15-second preview and stop for explicit preview approval. Preview approval authorizes only the full raw. Generate the full Avatar IV raw, run full-file QA, deliver it, and stop at `awaiting_raw_approval` for explicit approval bound to its video ID and SHA-256.
12. Only after the exact full raw is approved may `hyperframes:hyperframes` and `hyperframes:hyperframes-cli` add captions, graphics, optional BGM, branding, cover, and packaging. Keep the approved identity, lip sync, audio, and performance unchanged.

## Truthful generation status

The following are not rendering evidence:

- `thinking` with `progress=0`;
- a `blueprint` or draft resource;
- an empty video list;
- a visible 生成按钮;
- a blank or unbound avatar selector;
- a connector or chat message that says it started successfully.

In any of those states, 不得报告“正在生成”. Continue controlling the existing page or report a precise blocker. Never click Generate again merely because polling is slow.

## Motion and voice direction

Use the semantic plans, not fixed second-by-second choreography:

- Keep camera and framing fixed; no pan, zoom, cuts, crop jumps, or artificial shake.
- Maintain direct gaze with natural irregular blinks, subtle micro-expressions, calm breathing, and a stable torso.
- Use small phrase-led head motion and return to center.
- Use restrained hand gestures only when visible anatomy supports them. Complete one prepare-stroke-retract-cooldown cycle, then return hands to neutral before another gesture.
- Avoid repetitive swaying, continuous gesturing, mechanical face/head/hand synchrony, fused hands, or invented limbs.
- Derive faster/slower delivery, pauses, and emphasis from questions, warnings, contrasts, steps, explanations, and conclusions.

Read `references/performance-profiles.md` before building the motion block.

## Batch and approval safety

Process batch jobs 严格串行 with `scripts/queue_jobs.py`. If the queue head waits for image, preview, or raw approval, stop all later jobs. Never execute two jobs concurrently or transfer approval evidence between jobs.

Image approval, preview approval, raw approval, and HyperFrames approval are separate gates. Rights confirmation and spending consent authorize neither an image nor a video artifact.

## Local artifacts and recovery

`scripts/plan_job.py --dry-run` writes the seven compatible job files, including `heygen-app-plan.json`; its internal transport is `heygen-web-plan-credits`. A plan is not evidence that a browser action ran.

Use `scripts/update_job_state.py` for resumable v3 events and `scripts/migrate_job_state.py` for conservative v1/v2 migration. Reuse a recorded video ID after timeout. Retry only the failed stage; never submit a duplicate paid render to recover a poll or download.

## Required references

- Read `references/framework.md` for registry, state v3, queue, approvals, and recovery.
- Read `references/browser-submission.md` before every live HeyGen submission.
- Read `references/checklists.md` at each gate.
- Read `references/performance-profiles.md` before visual/performance planning.
- Read `references/api-facts.md` for current transport boundaries and volatile facts.
- Read `references/public-safety.md` when public distribution or disclosure matters.
