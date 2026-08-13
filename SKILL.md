---
name: rachel-digital-human-production
description: Use when the user invokes 数字人skill or asks to produce or batch-automate authorized Chinese HeyGen digital-human talking-head videos of 15 seconds or longer with a stable cloned voice and boss identity, optional company-material or B-roll integration, variable per-job looks, previews, natural semantic motion, exact artifact approvals, or ChatCut post-production.
---

# 数字人skill

## Core contract

Choose the narration provider separately for every job, then use the connected
HeyGen plugin for live animation. On the MiniMax branch, synthesize the exact
approved text with `huangxu1`, upload the exact MiniMax
audio to HeyGen, and prevent HeyGen from re-synthesizing or rewriting it. On
the HeyGen branch, prefer the structured `create_video_from_avatar` or
`create_video_from_image` tool so the approved script, HeyGen `voice1`, motion
prompt, aspect ratio, and resolution remain explicit.
Do not use the Video Agent generation tool when the script must remain
byte-for-byte because Video Agent may rewrite it. If an adopted image exists
only as a local file, allow only the HeyGen v3 asset-upload bridge needed to
turn that exact approved file into an asset ID; keep generation in the plugin.

Keep these long-term assets stable:

- `minimax_voice1`: the authorized MiniMax cloned voice `huangxu1`.
- HeyGen `voice1`: the authorized private HeyGen cloned voice resolved from the connected account at runtime.
- `image1`: the identity master. Preserve face shape, features, apparent age, skin tone, hairstyle, eyewear, body type, and recognizability.
- 原始图片1: the default per-job look when the user declines a new image.

Use the fixed local brand defaults in `references/brand-defaults.md`. Treat its
enterprise-AI IP, general-distribution profile, and `original_image1` artifact as
defaults for future jobs. These defaults never waive per-job authorization or
artifact approval gates.

Wardrobe, pose, background, lighting, framing, and props may vary by job. Identity may not.

## Candidate-image generation contract

Apply these rules whenever the built-in image model creates or revises a boss-look candidate.

### Identity source and four-candidate rounds

- Treat `image1` / `original_image1` as the immutable identity authority. Preserve the same fuller face and cheek volume, facial geometry, apparent age, natural skin tone and texture, hairline and short hairstyle, eyewear shape, ears, and broad body build. Do not beautify, slim the face, sharpen the jaw, enlarge the eyes, smooth away natural texture, make the subject younger, or substitute a similar person.
- Generate exactly four candidates in each image-generation round and label them `1` through `4`. Do not generate fewer, extra hidden variants, or an unrequested second batch.
- Generate all four candidates directly from `original_image1`; never use one generated candidate as another candidate's identity source.
- Keep identity, wardrobe, setting, framing, selected view mode, and expression direction consistent across all four. Require **four distinct two-hand pose families**, not four phases of one open-palm gesture. Vary the relationship, height, and orientation of both hands while keeping each pose restrained and Avatar IV-safe. At most one candidate may use the familiar one-open-palm-plus-one-flat-resting-hand pose. Do not change several major variables at once.
- Assign and record a concise **gesture signature** for each candidate before generation. The four signatures must be visibly different from one another and must avoid the gesture signature of the most recently adopted look when one exists. Never use one generic prompt with only “preparation / stroke / retract” substitutions.
- If the user says the person no longer matches the template, asks to regenerate from the original master, or identity drift is visible, exclude all generated candidates as image references and regenerate the next four from `original_image1` only. Describe retained non-identity choices in text.
- For a narrow revision of a user-selected image, `original_image1` remains the first and controlling identity reference. A selected candidate may be added only to preserve its approved wardrobe, setting, framing, or gesture. If references conflict, `original_image1` wins.

### Default pose, expression, hands, and composition

Use these defaults unless the user explicitly requests a different compatible choice:

- **45-degree side mode:** rotate head, neck, shoulders, and torso together about 45 degrees toward the selected side. The nose points diagonally toward that side, the far cheek visibly narrows, and both eyes remain visible so the result is a three-quarter view rather than frontal or a 90-degree profile. Anchor the gaze on a natural off-camera conversation point in the same direction; never twist the eyes back toward the lens.
- **Ordinary expression:** use a relaxed everyday neutral expression, neither smiling nor stern. Keep lips naturally closed, mouth corners neutral, brows relaxed, eyes calm and attentive, and cheeks neutral. Do not add a smile, micro-smile, visible teeth, squint, raised cheeks, laugh, frown, sales expression, promotional enthusiasm, or intense corporate seriousness unless the user explicitly asks for it.
- **Separated conversational hands:** keep both complete forearms and both complete hands visible with clear space between the hands. Select four different safe pose families per round, such as: (1) both hands resting separately with different wrist angles; (2) both hands lifted asymmetrically in a restrained two-hand explanation; (3) one hand near the torso with softly curved fingers while the other rests lower and farther away; (4) one compact palm-up gesture while the other rests on a different support. Treat these as pose-family examples, not a fixed repeating sequence. Do not clasp, cross, overlap, stack, interlace, or hide the hands. Avoid pointing, fists, folded arms, palm-to-palm symmetry, or theatrical gesture amplitude.
- **Hand anatomy:** require exactly five natural fingers on each visible hand, correct finger ownership and joints, plausible wrists, and no fusion, duplication, missing digits, melted anatomy, or detached limbs.
- **Framing:** use a vertical 9:16 seated medium close-up that keeps the face large enough for digital-human animation while retaining both hands and safe margins. Keep the camera natural and stable; no text, watermark, extra people, or distracting props.
- **Wardrobe and setting fallback:** when the user supplies no different direction, use a charcoal dark-gray knitted polo without a logo or microphone and a realistic warm modern executive lounge with wood, glass, soft daylight, and shallow depth of field. These are defaults, not identity traits, and may change per job.

Inspect all four candidates before display. A candidate that fails identity, the selected view mode, the requested expression, complete separated hands, finger anatomy, framing, or the assigned gesture signature is ineligible and must be identified as rejected. Also reject the round when two eligible candidates collapse to the same two-hand pose family. Do not silently generate more than four to replace it in the same round. Display the eligible candidates together, identify any rejected slot, and wait for the user's next instruction.

## Required job order

Execute every job in this order. Each decision belongs only to the current job.

1. Confirm authorization for the voice, portrait, script, use, and distribution. Use `get_current_user` to confirm the connected HeyGen account and its current subscription-credit source before spend; never hard-code a balance.
2. Ask exactly: **“这次配音使用 MiniMax，还是 HeyGen？”** Present MiniMax as recommended, then record `minimax` or `heygen` for this job. Do this for every job and never reuse an earlier voice-provider choice. Read `references/voice-routing.md` before resolving or generating narration.
3. Before drafting or rewriting any script, ask exactly: **“这个任务是否需要加入公司素材？”** Record an explicit yes/no for this job; never reuse an earlier answer. On explicit no, write the normal company talking-head script without material-dependent claims. On explicit yes, read `references/material-routing.md`, inventory the available real company materials first, then write material-grounded company copy that explicitly describes only capabilities supported by those materials. Never draft generic copy first and force materials into it afterward.
4. Resolve the selected narration route and `image1`. If the user requests a rewrite or the supplied Mandarin contains awkward phrasing or unsafe TTS breaks, read `references/brand-defaults.md`, rewrite it as natural spoken Mandarin, run the semantic-boundary checks, display the complete script, and wait for explicit script approval. Only then preserve the approved script exactly. Duration must be at least 15 seconds; there is no maximum script duration. If it is shorter than 15 seconds, present a rewrite and wait for approval. Do not create the final local plan until step 6 records the view mode.
5. Ask exactly: **“这个任务是否调用内置生图模型生成新的老板形象？”** Do this for 每个任务, even when a previous task used a generated look. If yes, read `references/view-modes.md`, ask exactly **“这次生成的老板形象采用正面，还是45°侧面（左转或右转）？”**, and record `front`, `three_quarter_left_45`, or `three_quarter_right_45` only for this job.
6. If the answer is no, select 原始图片1, record `original_image1`, and use `front`; do not claim it satisfies a new side-view request. If yes, follow the complete **Candidate-image generation contract** above and use the built-in image model to generate exactly four labeled candidates in one round. Run local planning with the recorded `view_mode` only after this choice.
7. Display the four exact candidate artifacts together and stop. Continue only after the user explicitly and unambiguously replies `采用第1张`, `采用第2张`, `采用第3张`, or `采用第4张`, or otherwise identifies exactly one candidate. A bare `采用` is ambiguous when four candidates are shown and requires a short clarification. Bind approval to the selected candidate's SHA-256 and artifact reference. `可以`, `继续`, silence, earlier authorization, or approval of another image does not count.
8. Retain every adopted look under the same boss identity group with a task-derived name. Never replace the `image1` identity master.
9. Ask: **“这个任务需要先生成15秒低成本预览吗？”** Record an explicit yes/no for this job. Do not reuse an earlier answer.
10. Read `references/plugin-submission.md`. Resolve the exact adopted look and the selected narration asset. Require the look to report `avatar_iv` capability. For a local adopted image, upload only its approved SHA-256 bytes through the v3 asset bridge, attach the resulting photo avatar to the existing `image1` group, wait until the new look is ready, then resolve its fresh look ID.
11. Before every preview or full-script synthesis, analyze that exact approved text and write a job-specific `voice-plan.json`. Divide only at punctuation or true semantic boundaries; for every segment record emotion, emotion intensity, speed, emphasis, pause direction, and its exact text. The segments must concatenate losslessly to the approved excerpt or full script. Use an amplified but controlled emotional arc with clearly audible contrast: push hooks, questions, warnings, reversals, and conclusions substantially above explanatory bridges, while capping emotion intensity at `0.85` to avoid shouting, theatrical delivery, or cloned-voice distortion. Do not default every segment to `calm`, and do not add, delete, paraphrase, or reorder text. Then build and re-read the route-specific payload. For `minimax`, synthesize the segments with `huangxu1`, join them in approved order, and require the exact approved MiniMax MP3 and its uploaded HeyGen audio asset ID; HeyGen must not re-synthesize the narration. For `heygen`, require the exact approved script and verified HeyGen `voice1`, and preserve the same voice direction in the payload. In both routes require portrait `9:16`, `720P`, captions off, the complete view-mode-aware motion prompt, and one submission. Reject a missing or mismatched asset, unsupported Avatar IV capability, wrong orientation or resolution, a missing motion prompt, a flat or missing emotion plan, lossless-text failure, or any provider fallback. Then call one structured generation tool once.
12. Persist the returned stable video ID immediately and poll that same ID with `get_video`. A tool success sentence alone is not execution evidence. Report `submitted` only after the plugin acknowledges the ID; report `rendering` only when provider status or progress proves rendering; never resubmit because polling is slow.
13. If preview was selected, use an approved opening excerpt targeting 15 seconds and preserve its characters and punctuation exactly. On `minimax`, synthesize and upload that excerpt as the exact driving audio; on `heygen`, submit the excerpt with verified HeyGen `voice1`. Measure the completed artifact and never call it exact 15 seconds unless the file verifies as 15.0 seconds. Deliver that preview and stop for explicit preview approval. Preview approval authorizes only the full raw. Generate the full route-specific raw, run full-file QA, deliver it, and stop at `awaiting_raw_approval` for explicit approval bound to its video ID and SHA-256.
14. After the exact full raw is approved, enter ChatCut post-production using the material route chosen in step 3. Read and use `chatcut:chatcut-plugin-basics`, `chatcut:talking-head-guide`, `chatcut:asset-import`, `chatcut:transcription`, `chatcut:music`, `chatcut:export`, and `chatcut:verification`. Keep the approved raw unchanged as the base. For the no-material route, apply the approved pacing, pause cleanup, dynamic captions, BGM, voice ducking, and flower text without company B-roll. For the material route, also follow the approved `material-plan.json`: select only the 1–2 real company asset categories most directly supported by the approved script, generate only 1–2 script-specific supporting assets when they fill distinct visual gaps, and place each asset at its material-grounded sentence using transcript timestamps. Preserve identity, lip sync, voice, and performance in both routes.

## Truthful generation status

The following are not rendering evidence:

- a connector/chat success sentence without a stable video ID;
- a stable ID that `get_video` does not acknowledge;
- `thinking`, `queued`, or `pending` with no provider evidence of rendering;
- a missing or mismatched avatar/look/voice binding;
- a Video Agent draft or blueprint that may rewrite the approved script.

In any of those states, 不得报告“正在生成”. Persist an acknowledged stable ID as `submitted`, poll that same ID, or report a precise blocker. Never submit again merely because polling is slow.

## Motion and voice direction

Use the semantic plans, not fixed second-by-second choreography:

- Keep camera and framing fixed; no pan, zoom, cuts, crop jumps, or artificial shake.
- For `front`, maintain direct gaze. For either 45° side mode, keep gaze on the same-direction off-camera conversation point and never twist the eyes back to the lens.
- Use natural irregular blinks, subtle micro-expressions, calm breathing, and a stable torso. Use small phrase-led head motion and return to the selected front or 45° pose-and-gaze anchor.
- Use restrained hand gestures only when visible anatomy supports them. Complete one prepare-stroke-retract-cooldown cycle, then return hands to neutral before another gesture.
- Avoid repetitive swaying, continuous gesturing, mechanical face/head/hand synchrony, fused hands, or invented limbs.
- Derive faster/slower delivery, pauses, and emphasis from questions, warnings, contrasts, steps, explanations, and conclusions.
- Before any TTS call, create `voice-plan.json` from the current approved script. Vary emotion and emotion intensity by semantic beat, using amplified but controlled contrast for hooks, questions, warnings, reversals, and conclusions while keeping explanatory bridges distinctly restrained. Cap emotion intensity at `0.85`.
- Preserve the approved text losslessly: concatenating every planned segment must reproduce the approved preview excerpt or full script byte-for-byte.
- Treat punctuation as the pause map. Never pause inside a complete Mandarin phrase merely to vary delivery; place pauses only at approved semantic boundaries.

Read `references/performance-profiles.md` before building the motion block.

## Batch and approval safety

Process batch jobs 严格串行 with `scripts/queue_jobs.py`. If the queue head waits for image, preview, or raw approval, stop all later jobs. Never execute two jobs concurrently or transfer approval evidence between jobs.

Voice-provider choice, material-route choice, image approval, preview approval, and raw approval are separate gates. Never transfer a voice or material choice between jobs or infer it from earlier editing preferences, silence, or rights/spending consent. ChatCut post-production may begin only after the exact full raw receives bound approval.

## Local artifacts and recovery

`scripts/plan_job.py --dry-run` writes the seven compatible job files, including `heygen-app-plan.json`; its internal transport is `heygen-plugin-structured`. A plan is not evidence that a plugin call ran.

Use `scripts/update_job_state.py` for resumable v3 events and `scripts/migrate_job_state.py` for conservative v1/v2 migration. Reuse a recorded video ID after timeout. Retry only the failed stage; never submit a duplicate paid render to recover a poll or download.

## Required references

- Read `references/framework.md` for registry, state v3, queue, approvals, and recovery.
- Read `references/voice-routing.md` immediately after the per-job MiniMax/HeyGen choice and before narration resolution.
- Read `references/plugin-submission.md` before every live HeyGen submission.
- Read `references/checklists.md` at each gate.
- Read `references/performance-profiles.md` before visual/performance planning.
- Read `references/api-facts.md` for current transport boundaries and volatile facts.
- Read `references/public-safety.md` when public distribution or disclosure matters.
- Read `references/brand-defaults.md` when resolving the fixed IP, distribution profile, original identity image, or a new job look.
- Read `references/view-modes.md` after choosing to generate a new boss look and before image or motion planning.
- Read `references/material-routing.md` immediately after an explicit yes to the company-material question and before drafting that job's script.
