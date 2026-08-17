# Production Checklists

Use each checklist at its named gate. A later gate never substitutes for an earlier one.

## Authorization and planning

- [ ] Confirm rights to `minimax_voice1`, HeyGen `voice1`, `image1`, the script, intended use, and distribution as applicable.
- [ ] Confirm the connected HeyGen account and subscription-credit source with `get_current_user`; never hard-code a balance.
- [ ] Record `interactive` or `auto` for this job only; on `auto`, read `references/auto-mode.md` and skip the confirmation questions below.
- [ ] Ask exactly: “这次配音使用 MiniMax，还是 HeyGen？” immediately after authorization.
- [ ] Record `minimax` or `heygen` only for this job; never inherit an earlier voice-provider choice.
- [ ] On MiniMax, require `huangxu1`; on HeyGen, resolve the private HeyGen `voice1` at runtime.
- [ ] Before every preview or full-script synthesis, create a new `voice-plan.json` from that exact approved text with per-segment emotion, emotion intensity, speed, emphasis, and pause direction.
- [ ] Verify the planned segment text concatenates losslessly and byte-for-byte to the approved input; reject inserted, deleted, paraphrased, or reordered text.
- [ ] Before drafting or rewriting the script, ask exactly: “这个任务是否需要加入公司素材？”
- [ ] Record explicit yes/no only for this job; never inherit an earlier material choice.
- [ ] On no, keep the normal talking-head script route without material-dependent claims.
- [ ] On yes, read `references/material-routing.md`, inventory real company assets first, and write material-grounded narration before asking for script approval.
- [ ] Resolve authorized registry records and verify local source SHA-256 values.
- [ ] Run preflight and `scripts/plan_job.py --dry-run`; parse all seven JSON artifacts.
- [ ] Confirm exact script preservation and an estimated duration of at least 15 seconds; do not impose a maximum duration.
- [ ] Before script approval, run a spoken-Mandarin read-aloud pass: reject awkward grammar, punctuation inside semantic units, and observed TTS risks from find_mandarin_tts_risks.

## Auto mode

- [ ] Record `operating_mode=auto` only after an explicit 全自动 request.
- [ ] Lock MiniMax, no company materials, `original_image1`, `front`, and preview disabled.
- [ ] Treat the supplied script as approved; rewrite TTS-unsafe phrasing without waiting; stop if shorter than 15 seconds.
- [ ] Run `scripts/plan_job.py --auto` then `apply-auto-defaults`.
- [ ] Submit one full raw; skip preview and new-look generation.
- [ ] Auto-approve raw only after QA pass with reviewer `auto-mode`.
- [ ] Enter ChatCut on the no-material route; never linger in an awaiting-approval state.

## Per-job image decision

- [ ] Ask “这个任务是否调用内置生图模型生成新的老板形象？” for this job.
- [ ] On no, select 原始图片1 and record `original_image1`.
- [ ] On yes, ask “这次生成的老板形象采用正面，还是45°侧面（左转或右转）？” and record the answer only for this job.
- [ ] On either side mode, verify the torso and head turn together about 45° and the gaze stays on the same-direction off-camera point without side-eye back to the lens.
- [ ] Generate exactly four candidates labeled `1` through `4`, each directly from `original_image1`; never use one generated candidate as another candidate's identity source.
- [ ] Keep identity, wardrobe, setting, framing, selected view mode, and requested expression consistent across all four; assign **four distinct two-hand pose families** and a unique **gesture signature** to every candidate. Use at most one candidate with one open palm and the other hand flat; include safe alternatives such as **both hands resting separately**, **both hands lifted asymmetrically**, and **one hand near the torso** with the other lower and farther away.
- [ ] Compare with the most recently or previously adopted look and exclude its gesture signature from the new round; reject any pair of candidates that collapses to the same two-hand pose family.
- [ ] Unless the user explicitly requests another expression, require an ordinary neutral face: closed lips, neutral mouth corners, relaxed brows and eyes, and no smile, micro-smile, raised cheeks, frown, sales expression, or intense corporate seriousness.
- [ ] Keep both forearms and hands fully visible and separated. Use one small-to-moderate open-palm conversational gesture while the other hand rests separately; reject clasping, crossing, overlap, stacked or interlaced hands, pointing, fists, folded arms, hidden hands, fused fingers, extra or missing fingers, and implausible wrists.
- [ ] Inspect all four for face, age, skin tone, hair, eyewear, body type, hands, mouth, crop, recognizability, and the selected 45-degree anchor. Mark invalid slots as rejected and do not silently generate replacement extras in the same round.
- [ ] Display all four together and stop until the user explicitly identifies one exact artifact, such as “采用第2张”; treat a bare “采用” as ambiguous.
- [ ] Bind approval to the selected candidate's SHA-256 and stable reference; do not accept generic continuation.
- [ ] Retain the adopted look in the same identity group with a task-derived name.

## Per-job preview decision

- [ ] Ask whether this job needs a 15-second low-cost preview only after the image is selected.
- [ ] Record explicit yes/no; never reuse a previous job answer.
- [ ] If yes, require approval of the exact preview before full-raw submission.
- [ ] If no, proceed directly to the full raw after all plugin pre-spend checks.

## HeyGen plugin pre-spend

- [ ] Read `references/plugin-submission.md`.
- [ ] Use the connected HeyGen plugin and its reported subscription-credit source.
- [ ] Resolve or upload the exact approved look; for local images allow only the HeyGen v3 asset bridge.
- [ ] Verify the approved look matches the recorded `front`, `three_quarter_left_45`, or `three_quarter_right_45` mode.
- [ ] Verify the look is ready, belongs to `image1`, and supports `avatar_iv`.
- [ ] Read the recorded narration provider and reject a missing or inherited choice.
- [ ] On MiniMax, verify `huangxu1`, synthesize the approved text according to the current `voice-plan.json`, and upload the exact MiniMax audio with its bound SHA-256. HeyGen must not re-synthesize it.
- [ ] On HeyGen, resolve the exact stable HeyGen `voice1` ID with `get_voice` and submit the verbatim script.
- [ ] Pass the verbatim script on HeyGen or the exact MiniMax audio asset on MiniMax; never pass both narration sources.
- [ ] Omit `voiceSettings` by default; use a video-tool voice field only after the same video endpoint and same voice have produced an intelligible, duration-consistent preview.
- [ ] Set portrait `9:16`, `720P`, and captions off.
- [ ] Preserve the full semantic voice direction and motion prompt.
- [ ] Use `create_video_from_avatar` or `create_video_from_image`; reject Video Agent for exact-script jobs.
- [ ] For a preview, use an approved opening excerpt targeting 15 seconds and require actual-duration QA.
- [ ] Submit once only after every field passes.

## Real-render evidence

- [ ] Persist the stable video ID returned by the plugin immediately.
- [ ] Require `get_video` to acknowledge that exact ID before reporting submitted.
- [ ] Report rendering only when provider status/progress proves it.
- [ ] Report completed only when a real completed video resource exists.
- [ ] Do not trust a connector/chat “success” sentence as evidence.
- [ ] Poll the existing video ID; never submit again because polling is slow.

## Motion, voice, and full-file QA

- [ ] Verify speed, pauses, emphasis, and emotion vary by semantic beat.
- [ ] Verify emotion intensity uses amplified but controlled contrast: when high-impact and explanatory beats both exist, require at least `0.45` intensity separation, cap every segment at `0.85`, and reject all-`calm`, shouting, theatrical, or identity-distorting delivery.
- [ ] Verify every pause follows approved punctuation or a true semantic boundary; reject any pause inside a subject-predicate, verb-object/complement, fixed phrase, proper noun, or number-plus-unit.
- [ ] Verify fixed camera and framing: no pan, zoom, tilt, crop jump, cuts, or shake.
- [ ] For front mode, verify direct gaze. For a 45° side mode, verify the off-camera gaze anchor and reject any eye twist back to the lens.
- [ ] Verify irregular blinks, subtle expressions, calm breathing, stable torso, and phrase-led head movement returning to the selected view anchor.
- [ ] Pair each gaze change with a small head adjustment plus eyelid/brow response; reject pupil-only motion, rapid eye scans, and forced continuous smiling.
- [ ] Verify each visible-hand gesture completes prepare, stroke, retract, cooldown, then neutral.
- [ ] Reject pendulum motion, repetitive gestures, mechanical synchrony, fused anatomy, or invented limbs.
- [ ] Decode the complete media; verify duration, audio, lip sync, first/last word, and first/last frame.
- [ ] Listen to the complete preview; fail voice QA when speech is unintelligible, differs from the approved text or selected voice, or is materially longer than its estimate or prior baseline.
- [ ] Confirm HeyGen did not re-synthesize the exact MiniMax audio and that no silent provider fallback occurred.
- [ ] Record stable video ID, exact artifact SHA-256/reference, and strict QA result.

## Exact approvals and ChatCut

- [ ] Deliver the named preview/raw artifact and stop at its approval state.
- [ ] Bind approval only to the exact artifact the user explicitly approved, except auto mode after a QA-passed full raw.
- [ ] Keep material-route choice, image, preview, and raw approvals separate.
- [ ] Do not substitute rights consent, spending consent, automatic QA, silence, or an earlier “继续” in interactive mode.
- [ ] In auto mode, bind raw approval only with reviewer `auto-mode` after QA pass; never auto-approve a failed QA or a generated look.
- [ ] Start ChatCut post-production only after bound full-raw approval.
- [ ] On the no-material route, add pacing, pause cleanup, dynamic captions, BGM, voice ducking, and flower text without company B-roll.
- [ ] On the material route, verify every selected real asset has material-grounded narration, use only the 1–2 most relevant real company-asset categories, and never串联全部素材 merely to fill the timeline.
- [ ] Create `material-plan.json`, generate only 1–2 AI supporting assets for distinct visual gaps, add “场景示意” when needed, and place assets from word-level transcript timestamps.
- [ ] Use the approved raw unchanged as the base; preserve identity, lip sync, voice, and performance.
- [ ] Run ChatCut project-structure, timeline, caption, audio, visual, full-export, and final-media QA.

## Batch and archive

- [ ] Use the strict FIFO queue; never run two jobs concurrently.
- [ ] Stop all later jobs while the head waits for image, preview, or raw approval.
- [ ] Archive script, seven plans, state v3, approved look, stable IDs, hashes, QA, evidence, raw/final media, and retry notes.
- [ ] Confirm no credentials, headers, temporary URLs, or embedded private media are stored.
- [ ] Mark `complete` only after final-file QA passes.
