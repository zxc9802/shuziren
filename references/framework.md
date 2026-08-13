# Modular Digital Human Framework

## Identity and job looks

The registry is the trust boundary. `minimax_voice1` is the stable MiniMax voice `huangxu1`, HeyGen `voice1` is the connected account's private cloned voice, and `image1` is the boss identity master. Store only authorized local fingerprints and stable remote IDs; never store credentials, headers, temporary URLs, or raw provider payloads.

Every job begins with four independent per-job choices plus one conditional look choice:

1. whether narration uses MiniMax or HeyGen;
2. whether to use the company-material route;
3. whether to generate a new four-candidate boss-look round;
4. when generating a new look, whether it is front, left 45°, or right 45°;
5. whether to generate a 15-second preview.

Ask “这次配音使用 MiniMax，还是 HeyGen？” immediately after authorization, record only `minimax` or `heygen`, and read `references/voice-routing.md`. Never reuse an earlier voice-provider choice. Then ask “这个任务是否需要加入公司素材？” before drafting or rewriting the script. A no answer keeps the normal talking-head script route. A yes answer requires reading `references/material-routing.md`, inventorying real company assets, and writing the narration around only the capabilities those assets support. Then ask the image question. A no answer selects `original_image1`. A yes answer requires the exact front/left-45°/right-45° question from `references/view-modes.md` and creates exactly four labeled built-in-model candidates directly from `original_image1` under the Candidate-image generation contract in `SKILL.md`. Keep identity, wardrobe, setting, framing, approved view mode, and requested expression consistent across the four; vary only restrained non-identity details such as gesture phase, shoulder relaxation, and composition balance. Display the four together. The selected candidate cannot become the sole job image until the user explicitly identifies it, such as “采用第2张”; a bare “采用” is ambiguous. Record only the selected candidate through the single-image approval state and retain an adopted look in the same identity group with a task-derived name; never overwrite `image1`.

## Seven planning artifacts

`scripts/plan_job.py --dry-run` performs no network calls and atomically creates:

1. `task.json`: exact script, duration, aliases, pending image/preview choices, recorded `view_mode`, settings, overrides.
2. `content-beats.json`: character-preserving semantic beats.
3. `voice-plan.json`: the exact approved text segmented losslessly by semantic beat, with per-segment speed, pause, emphasis, emotion, and emotion intensity. Create it before every preview or full-script synthesis; never reuse a preview plan as the full-script plan.
4. `visual-plan.json`: identity master, job-look policy, scene, framing, pose, topology, QA.
5. `performance-plan.json`: face, head, hand, and body behavior with complete gesture cycles.
6. `heygen-app-plan.json`: backward-compatible filename containing the `heygen-plugin-structured` action plan.
7. `state.json`: v3 state at `planned`, with image/preview/raw approvals false.

Planning is valid for scripts estimated at 15 seconds or longer, with no maximum duration, and preserves the submitted text exactly.

## Connected HeyGen plugin transport

Live generation uses the connected HeyGen plugin and the subscription-credit source reported by `get_current_user`. Use structured avatar/image video tools for exact scripts. The only direct transport exception is the HeyGen v3 asset upload needed to convert an approved local image into an asset ID.

Execute the plugin plan in this order:

```text
inspect connected account
-> resolve or upload exact approved look
-> verify Avatar IV capability
-> resolve exact MiniMax audio asset or HeyGen voice1 from the recorded route
-> verify the approved look matches the recorded view mode
-> build the route-specific payload with exact MiniMax audio or verbatim HeyGen script, 9:16, 720P, captions off, and view-mode-aware motion prompt
-> verify every pre-spend field
-> call one structured plugin generation tool once
-> persist and verify the returned stable video ID
-> poll the existing stable video ID
```

Do not use `video_agent_generate` for a byte-for-byte approved script because it may rewrite the narration. On the MiniMax route, upload the exact MiniMax audio and HeyGen must not re-synthesize it. Do not ask the user to bind assets manually or repeat setup represented by stable IDs. If the plugin cannot resolve the private look, selected audio, or selected voice, stop with the exact blocker and never silently switch providers.

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

A connector success sentence, an unacknowledged ID, `thinking/queued/pending` without provider rendering evidence, a blueprint/draft, or a missing asset binding never enters a rendering state. Persist an acknowledged stable ID as submitted; `render-started` requires observable provider rendering evidence. Slow polling reuses that ID and never causes a second paid submission.

## Strict FIFO batches

Queue files are strict JSON: `{"version":1,"job_ids":[...]}`. `scripts/queue_jobs.py next` returns only the first actionable job or `blocked`. Completed heads are skipped. Any head at `awaiting_image_approval`, `awaiting_preview_approval`, or `awaiting_raw_approval` blocks every later job. Never run two jobs concurrently.

## Approval boundaries

- Material-route choice determines normal versus material-grounded script and ChatCut packaging for the current job only.
- Voice-provider choice determines MiniMax external audio versus HeyGen `voice1` for the current job only.
- Image approval selects only the generated look.
- Preview approval permits only full-raw generation.
- Raw approval permits only the transition to post-production.
- After raw approval, use ChatCut with the route explicitly recorded before script drafting. The normal route adds pacing, pause cleanup, dynamic captions, BGM, voice ducking, and flower text without company B-roll. The material route uses only the 1–2 类真实公司素材 most relevant to the approved script, adds only 1–2 个 AI 补充素材 for distinct visual gaps, and follows transcript-timed placement from `material-plan.json`; never串联全部素材 merely to fill the timeline.
- ChatCut may start only after `post_production` validates the bound full-raw approval.

Rights confirmation, account authorization, credit-spend consent, automatic QA, silence, “继续”, or approval of another artifact cannot substitute.

## Recovery and migration

- Inspect state before each live action and persist stable evidence immediately.
- Reuse complete voice/identity assets and approved looks; do not clone or upload duplicates. Reuse a verified exact MiniMax audio upload by hash within the same job only.
- Continue polling the existing video ID after timeout.
- Fetch a result again after a temporary download URL expires; do not rerender.
- Migrate v1/v2 conservatively. Ambiguous old jobs return to `planned` and must answer the image and preview questions again.
- Preserve only schema-valid stable IDs and local fingerprints. Never infer image/preview authority from old statuses.
