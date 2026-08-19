---
name: 数字人
description: Use when the user invokes 数字人skill or asks to produce or batch-automate authorized Chinese HeyGen digital-human talking-head videos of 15 seconds or longer with a stable cloned voice and boss identity, optional company-material or B-roll integration, variable per-job looks, previews, natural semantic motion, exact artifact approvals, ChatCut post-production with script-grounded MG, or a full-auto mode that takes a supplied script and finishes without mid-flow confirmations.
---

# 数字人skill

## Core contract

Choose the narration provider separately for every job, then use the connected
HeyGen plugin for live animation. On the MiniMax branch, synthesize the exact
approved text with `huangxu1`, upload the exact MiniMax
audio to HeyGen, and prevent HeyGen from re-synthesizing or rewriting it. On
the IndexTTS-2 branch, synthesize the exact approved text through 302.AI
IndexTTS-2 with `indextts_voice1`, upload that exact audio to HeyGen, and
prevent HeyGen from re-synthesizing or rewriting it. On
the HeyGen branch, prefer the structured `create_video_from_avatar` or
`create_video_from_image` tool so the approved script, HeyGen `voice1`, motion
prompt, aspect ratio, and resolution remain explicit.
Do not use the Video Agent generation tool when the script must remain
byte-for-byte because Video Agent may rewrite it. When an adopted image or
approved narration exists only as a local file, prefer the same-account HeyGen
v3 asset-upload bridge. If the connected plugin cannot upload local files, use
the verified temporary HTTPS bridge below to expose only those exact approved
bytes; keep avatar creation and video generation in the connected plugin.

Keep these long-term assets stable:

- `minimax_voice1`: the authorized MiniMax cloned voice `huangxu1`.
- `indextts_voice1`: the authorized IndexTTS-2 speaker-reference clip resolved from `INDEXTTS_SPEAKER_AUDIO_URL` in the local `.env`.
- HeyGen `voice1`: the authorized private HeyGen cloned voice resolved from the connected account at runtime.
- `image1`: the stable boss identity shared by the approved front and side master images. Preserve face shape, features, apparent age, skin tone, hairstyle, eyewear, body type, and recognizability.
- `original_image1`: the front-view identity master and the default per-job look when the user declines a new image.
- `side_image1`: the side-view identity master at `assets/side-image1.jpg`, SHA-256 `4b50ae645a5056247dba83aa9b660450bb3dc3e9d3df90c56adabfb72c787013`. Whenever the user selects either 45-degree side mode, use this exact image as the first and controlling person reference.

Keep the two masters separate: `front` routes to `original_image1`; both
`three_quarter_left_45` and `three_quarter_right_45` route to `side_image1`.
The selected view mode controls the output's left/right direction, so the
reference image's current facing direction does not override the user's choice.
Use `side_image1` for the person's identity and side-face geometry only; do not
inherit its navy polo, sofa, clasped hands, background, framing, or open-mouth
expression unless the current job explicitly requests those elements.

Use the fixed local brand defaults in `references/brand-defaults.md`. Treat its
enterprise-AI IP, general-distribution profile, and `original_image1` artifact as
defaults for future jobs. In interactive mode these defaults never waive
per-job authorization or artifact approval gates. In auto mode they feed the
locked route in `references/auto-mode.md` instead of asking.

Wardrobe, pose, background, lighting, framing, and props may vary by job. Identity may not.

When a job generates a new look, choose the image model separately for that
job: OpenLux `gpt-image-2-c` or the Codex built-in image model. Never reuse an
earlier image-model choice. Load OpenLux credentials only from the local
`.env`; never write the API key into SKILL.md, registries, prompts, logs, or
deliverables. The job's authorization must cover sending the identity master
to OpenLux before that route is used.

## Verified temporary HTTPS bridge for local assets

Use this bridge only when the connected HeyGen tool requires an HTTPS URL or
same-account asset ID and the approved image or narration exists only on the
computer. The job's authorization must cover sending those media files to
HeyGen.

1. Stage only the exact approved image and/or audio in a fresh temporary
   directory. Never serve a workspace root, home directory, credentials,
   scripts, state files, API keys, or unrelated media.
2. Start a loopback-only local file server, then actively establish a temporary
   public HTTPS tunnel to that server. A computer without a working tunnel is a
   transport problem to diagnose, not an immediate handoff to the user.
3. If the first tunnel cannot be reached—for example, the tunnel reports HTTP
   `530`, its outbound protocol or port is blocked, or the public URL cannot
   fetch the file—keep the same staged bytes, inspect the exact failure, and
   try another safe tunnel transport that runs over standard HTTPS port `443`.
   Do not regenerate or substitute the media merely to change transport.
4. Before any provider call, download every public URL back and require HTTP
   `200`, the expected media type, a complete non-empty body, and SHA-256 equal
   to the approved local artifact. A browser landing page, warning page,
   truncated response, redirect to unrelated content, or hash mismatch is a
   failed bridge.
5. For a photo-avatar creation timeout, list the target identity group's looks
   and search by the requested task-derived name before retrying. For a video
   submission timeout, recover and poll the existing stable video ID. Never
   create duplicate looks or duplicate paid renders because a connector timed
   out.
6. Keep the local server and tunnel alive until the new look is ready and every
   URL-driven video has completed, unless HeyGen explicitly confirms that it
   has fully ingested the source asset. Then stop both processes and report
   that the temporary public path is closed.
7. Keep temporary URLs and tunnel credentials out of long-term registries and
   final deliverables. Persist only the bridge method, approved hashes, provider
   asset/look/video IDs, and exact transport errors needed for recovery.

Only after safe tunnel attempts are exhausted may the job stop with the exact
blocker and request a user-hosted HTTPS URL or a same-account HeyGen asset ID.
Never replace the approved image, narration, account, or provider to bypass an
HTTPS failure.

## Candidate-image generation contract

Apply these rules whenever the selected image model — OpenLux `gpt-image-2-c` or the Codex built-in model — creates or revises a boss-look candidate.

### Identity source and four-candidate rounds

- Treat `image1` as the immutable identity authority represented by two approved view-specific masters. Before image generation, set `selected_identity_master` from the recorded view mode: `original_image1` for `front`, or `side_image1` for either 45-degree side mode. Preserve the same fuller face and cheek volume, facial geometry, apparent age, natural skin tone and texture, hairline and short hairstyle, eyewear shape, ears, and broad body build. Do not beautify, slim the face, sharpen the jaw, enlarge the eyes, smooth away natural texture, make the subject younger, or substitute a similar person.
- Generate exactly four candidates in each image-generation round and label them `1` through `4`. Do not generate fewer, extra hidden variants, or an unrequested second batch.
- Generate all four candidates directly from the recorded `selected_identity_master`; never use one generated candidate as another candidate's identity source. For side generation, every candidate must include the exact `side_image1` bytes as the person reference.
- Keep identity, wardrobe, setting, framing, selected view mode, and expression direction consistent across all four. Require **four distinct two-hand pose families**, not four phases of one open-palm gesture. Vary the relationship, height, and orientation of both hands while keeping each pose restrained and Avatar IV-safe. At most one candidate may use the familiar one-open-palm-plus-one-flat-resting-hand pose. Do not change several major variables at once.
- Assign and record a concise **gesture signature** for each candidate before generation. The four signatures must be visibly different from one another and must avoid the gesture signature of the most recently adopted look when one exists. Never use one generic prompt with only “preparation / stroke / retract” substitutions.
- If the user says the person no longer matches the template, asks to regenerate from the master, or identity drift is visible, exclude all generated candidates as image references and regenerate the next four from the recorded `selected_identity_master` only. Describe retained non-identity choices in text.
- For a narrow revision of a user-selected image, the recorded `selected_identity_master` remains the first and controlling identity reference. A selected candidate may be added only to preserve its approved wardrobe, setting, framing, or gesture. If references conflict, the view-specific master wins.

### Default pose, expression, hands, and composition

Use these defaults unless the user explicitly requests a different compatible choice:

- **45-degree side mode:** rotate head, neck, shoulders, and torso together about 45 degrees toward the selected side. The nose points diagonally toward that side, the far cheek visibly narrows, and both eyes remain visible so the result is a three-quarter view rather than frontal or a 90-degree profile. Anchor the gaze on a natural off-camera conversation point in the same direction; never twist the eyes back toward the lens.
- **Ordinary expression:** use a relaxed everyday neutral expression, neither smiling nor stern. Keep lips naturally closed, mouth corners neutral, brows relaxed, eyes calm and attentive, and cheeks neutral. Do not add a smile, micro-smile, visible teeth, squint, raised cheeks, laugh, frown, sales expression, promotional enthusiasm, or intense corporate seriousness unless the user explicitly asks for it.
- **Separated conversational hands:** keep both complete forearms and both complete hands visible with clear space between the hands. Select four different safe pose families per round, such as: (1) both hands resting separately with different wrist angles; (2) both hands lifted asymmetrically in a restrained two-hand explanation; (3) one hand near the torso with softly curved fingers while the other rests lower and farther away; (4) one compact palm-up gesture while the other rests on a different support. Treat these as pose-family examples, not a fixed repeating sequence. Do not clasp, cross, overlap, stack, interlace, or hide the hands. Avoid pointing, fists, folded arms, palm-to-palm symmetry, or theatrical gesture amplitude.
- **Hand anatomy:** require exactly five natural fingers on each visible hand, correct finger ownership and joints, plausible wrists, and no fusion, duplication, missing digits, melted anatomy, or detached limbs.
- **Framing:** use a vertical 9:16 seated medium close-up that keeps the face large enough for digital-human animation while retaining both hands and safe margins. Keep the camera natural and stable; no text, watermark, extra people, or distracting props.
- **Wardrobe and setting fallback:** when the user supplies no different direction, use a charcoal dark-gray knitted polo without a logo or microphone and a realistic warm modern executive lounge with wood, glass, soft daylight, and shallow depth of field. These are defaults, not identity traits, and may change per job.

### Photographic realism and view-specific geometry

Read `references/realism.md` before writing any image prompt. Match every candidate to the documentary handheld-video-frame look of the approved masters, not a studio-advertising or CG-render look. Apply all of the following to both front and side generation:

- **Skin:** preserve visible pores, mild natural shine, slightly uneven skin tone, and small real-life imperfections. Ban beauty retouching, skin smoothing, plastic or waxy skin, and over-sharpened "AI portrait" texture.
- **Camera:** render as a natural video-frame capture with modest dynamic range, faint sensor noise, and shallow but believable depth of field. Ban HDR glow, cinematic color grading, and over-polished studio lighting.
- **Eyewear:** require real lens behavior — visible environmental reflections on the lenses and a slight refraction offset of the cheek or jaw contour seen through the lens edge. Lenses must never read as empty frames.
- **Light:** every light must have a plausible source such as window daylight or practical lamps. Ban sourceless even fill and floating rim light.
- **Fabric:** clothing must show real weave, natural collar collapse, and seated-posture wrinkles, never smooth 3D-render cloth.

For either 45-degree side mode, additionally verify side-view geometry against `side_image1`: correct perspective foreshortening of the far eye, the nose bridge partially occluding the far eye corner, natural ear position and ear-to-jawline junction, correct perspective of the near glasses temple arm, and a natural hairline transition at the temple. Because `side_image1` records only one real facing direction, when generating the mirrored side describe the subject's asymmetric details — hair part direction and any facial asymmetry — explicitly in text; never let the model silently mirror them.

Inspect all four candidates before display. A candidate that fails identity, the selected view mode, the requested expression, complete separated hands, finger anatomy, framing, photographic realism, side-view geometry, or the assigned gesture signature is ineligible and must be identified as rejected. Also reject the round when two eligible candidates collapse to the same two-hand pose family. Do not silently generate more than four to replace it in the same round. Display the eligible candidates together, identify any rejected slot, and wait for the user's next instruction.

## Operating mode

Record `interactive` or `auto` only for the current job. Interactive is the
default. Record `auto` when the user asks for 全自动, 自动模式, or 不用确认,
or supplies a script and says the job should finish without mid-flow
approvals. Never infer auto from silence or from an earlier job.

On `auto`, read `references/auto-mode.md` and follow **Auto job order**
instead of asking the voice, material, image, preview, or raw-approval
questions. Same-turn explicit overrides may change only the named auto
default. Hard verification stops still apply.

## Auto job order

Use this order only when `operating_mode` is `auto`.

1. Confirm the connected HeyGen account with `get_current_user` before spend.
   Invoking auto with a script is this job's rights and credit-spend consent.
2. Record MiniMax `huangxu1`, no company materials, `original_image1`,
   `front`, and preview disabled. Do not ask MiniMax vs HeyGen vs IndexTTS-2, company
   materials, a new boss look, or a 15-second preview.
3. Treat the supplied copy as the approved script. Rewrite awkward or
   TTS-unsafe Mandarin in place and continue. If it is shorter than 15
   seconds, stop; do not invent extra sentences.
4. Plan with `scripts/plan_job.py --auto --dry-run`, then apply
   `apply-auto-defaults` so the job reaches `preview_choice_recorded` on
   原始图片1 with preview disabled.
5. Run `python3 scripts/verify_performance_reference.py --json`, read `references/performance-system.md`, and require the planned `business-human-123-v1` performance-only binding plus the exact versioned primitive-library binding. Then resolve the existing Avatar IV look for `original_image1`. Write `voice-plan.json`, synthesize its MiniMax segments, preserve their exact final-audio boundaries, and run `scripts/build_performance_beat_map.py`; require `performance-beat-map.json` to bind the exact final-audio SHA-256 before uploading that audio. Submit one structured full raw: portrait `9:16`, `720P`, captions off.
6. Persist and poll the same video ID. After download, run `scripts/compare_performance_reference.py` and the complete realism gate. `reject_and_rerender`, a missing evidence pack, or any other QA failure is a hard stop.
7. On QA pass, bind raw approval with reviewer `auto-mode` via
   `approve-raw-auto`, then enter ChatCut on the no-material route and
   deliver the packaged video.

## Required job order

Execute every interactive job in this order. Each decision belongs only to the current job.

1. Confirm authorization for the voice, portrait, script, use, and distribution. Use `get_current_user` to confirm the connected HeyGen account and its current subscription-credit source before spend; never hard-code a balance.
2. Ask exactly: **“这次配音使用 MiniMax，HeyGen，还是 IndexTTS-2？”** Present MiniMax as recommended, then record `minimax`, `heygen`, or `indextts` for this job. Do this for every job and never reuse an earlier voice-provider choice. Read `references/voice-routing.md` before resolving or generating narration.
3. Before drafting or rewriting any script, ask exactly: **“这个任务是否需要加入公司素材？”** Record an explicit yes/no for this job; never reuse an earlier answer. On explicit no, write the normal company talking-head script without material-dependent claims. On explicit yes, read `references/material-routing.md`, inventory the available real company materials first, then write material-grounded company copy that explicitly describes only capabilities supported by those materials. Never draft generic copy first and force materials into it afterward.
4. Resolve the selected narration route and `image1`. If the user requests a rewrite or the supplied Mandarin contains awkward phrasing or unsafe TTS breaks, read `references/brand-defaults.md`, rewrite it as natural spoken Mandarin, run the semantic-boundary checks, display the complete script, and wait for explicit script approval. Only then preserve the approved script exactly. Duration must be at least 15 seconds; there is no maximum script duration. If it is shorter than 15 seconds, present a rewrite and wait for approval. Do not create the final local plan until step 6 records the view mode.
5. Ask exactly: **“这个任务是否生成新的老板形象？”** Do this for 每个任务, even when a previous task used a generated look. If yes, read `references/view-modes.md`, ask exactly **“这次生成的老板形象采用正面，还是45°侧面（左转或右转）？”**, and record `front`, `three_quarter_left_45`, or `three_quarter_right_45` only for this job. Then record `selected_identity_master`: `original_image1` for `front`, or `side_image1` for either side mode. Then, before any image call, ask exactly: **“这次生图使用 OpenLux，还是 Codex 内置模型？”** Record `openlux` or `codex` only for this job. Never reuse an earlier image-model choice. Read `references/image-model-routing.md` before generating.
6. If the answer is no, select 原始图片1, record `original_image1`, and use `front`; do not claim it satisfies a new side-view request. If yes, read `references/realism.md`, follow the complete **Candidate-image generation contract** above, and generate exactly four labeled candidates in one round from the recorded `selected_identity_master` using the recorded image-model route. On `openlux`, call `scripts/generate_openlux_candidates.py` with the exact master bytes and four distinct prompts; do not silently fall back to Codex. On `codex`, use the Codex built-in image model with the same master as the first reference. Run local planning with the recorded `view_mode` and identity-master alias only after this choice.
7. Display the four exact candidate artifacts together and stop. Continue only after the user explicitly and unambiguously replies `采用第1张`, `采用第2张`, `采用第3张`, or `采用第4张`, or otherwise identifies exactly one candidate. A bare `采用` is ambiguous when four candidates are shown and requires a short clarification. Bind approval to the selected candidate's SHA-256 and artifact reference. `可以`, `继续`, silence, earlier authorization, or approval of another image does not count.
8. Retain every adopted look under the same boss identity group with a task-derived name. Never replace the `image1` identity master.
9. Ask: **“这个任务需要先生成15秒低成本预览吗？”** Record an explicit yes/no for this job. Do not reuse an earlier answer.
10. Read `references/plugin-submission.md`. Resolve the exact adopted look and the selected narration asset. Require the look to report `avatar_iv` capability. For a local adopted image, send only its approved SHA-256 bytes through the same-account v3 asset bridge or, when local upload is unavailable, the verified temporary HTTPS bridge above. Attach the resulting photo avatar to the existing `image1` group, wait until the new look is ready, then resolve its fresh look ID.
11. Before every preview or full-script synthesis, run `python3 scripts/verify_performance_reference.py --json`, read `references/performance-profiles.md`, and require `performance-plan.json` to bind the verified `business-human-123-v1` reference as performance-only. The reference controls whole-person speech coupling, living idle, gaze/eyelid variation, gesture cycles, and total-track continuity only; never copy or upload its identity, voice, wording, wardrobe, background, captions, aspect ratio, or exact timestamps. Then analyze the exact approved text and write a job-specific `voice-plan.json`. Divide only at punctuation or true semantic boundaries; for every segment record emphasis, pause direction, exact text, and provider-specific delivery. MiniMax plans record internal `director_intensity` plus the resolved supported `emotion` and numeric `speed`; IndexTTS-2 plans record `emotion_intensity` plus the exact eight-float vector; never send MiniMax director metadata as provider fields. The segments must concatenate losslessly to the approved excerpt or full script. Use an amplified but controlled emotional arc with clearly audible contrast: push hooks, questions, warnings, reversals, and conclusions substantially above explanatory bridges, while capping MiniMax `director_intensity` and provider emotion intensity at `0.85` to avoid shouting, theatrical delivery, or cloned-voice distortion. Do not default every segment to `calm`, and do not add, delete, paraphrase, or reorder text. Then build and re-read the route-specific payload. For `minimax`, build the allowlisted payload with `scripts.dhflow.minimax.build_task_payload`, synthesize the segments with `huangxu1`, join them in approved order, and require the exact approved MiniMax MP3 through either its same-account HeyGen audio asset ID or a SHA-256-verified temporary HTTPS URL; HeyGen must not re-synthesize the narration. For `indextts`, run `scripts/synthesize_indextts.py` on that `voice-plan.json`, join the exact IndexTTS-2 WAV segments in approved order, and require the exact approved audio through either its same-account HeyGen audio asset ID or a SHA-256-verified temporary HTTPS URL; HeyGen must not re-synthesize the narration. For `heygen`, require the exact approved script and verified HeyGen `voice1`, and preserve the same voice direction in the payload. In both routes require portrait `9:16`, `720P`, captions off, the complete view-mode-aware motion prompt, and one submission. Reject a missing or mismatched performance reference or asset, unsupported Avatar IV capability, wrong orientation or resolution, a missing motion prompt, a ban-dominated motion prompt or one that omits the living idle floor, a flat or missing emotion plan, repetitive dead-silence restarts, lossless-text failure, or any provider fallback. Then call one structured generation tool once.
   As part of step 11, read `references/performance-system.md`, require the exact versioned primitive-library hash and one legal semantic-relative `primitive_chain` per beat, and never claim frame-accurate HeyGen control. On `minimax` or `indextts`, preserve measured final-audio segment boundaries in `final-audio-segments.json`, run `scripts/build_performance_beat_map.py`, and require the resulting `performance-beat-map.json` to bind the exact uploaded audio SHA-256. On `heygen`, do not invent pre-render timestamps; derive the QA-only beat map after rendered audio exists.
12. Persist the returned stable video ID immediately and poll that same ID with `get_video`. A tool success sentence alone is not execution evidence. Report `submitted` only after the plugin acknowledges the ID; report `rendering` only when provider status or progress proves rendering; never resubmit because polling is slow.
13. If preview was selected, use an approved opening excerpt targeting 15 seconds and preserve its characters and punctuation exactly. On `minimax` or `indextts`, synthesize and upload that excerpt as the exact driving audio; on `heygen`, submit the excerpt with verified HeyGen `voice1`. Measure the completed artifact and never call it exact 15 seconds unless the file verifies as 15.0 seconds. Run the **realism QA gate** in `references/realism.md` on the completed preview before delivery: skin must not look retouched or plastic, glasses reflections must track head motion, resting hands must not freeze into a wax-figure pose, breathing must stay visible so the person never reads as a statue with a moving mouth, head motion must carry a neck-and-shoulder response, facial geometry and hands must not warp or melt during motion, and background bokeh must stay stable. A realism-gate failure makes the preview ineligible; do not treat it as a post-production fix. Deliver only a passing preview and stop for explicit preview approval. Preview approval authorizes only the full raw. Generate the full route-specific raw, run full-file QA including the same realism gate, deliver it, and stop at `awaiting_raw_approval` for explicit approval bound to its video ID and SHA-256.
   As part of step 13, run `scripts/compare_performance_reference.py` on every downloaded preview and full raw, and preserve `performance-qc.json`, `realism-review.md`, and `comparison-contact-sheet.jpg`. `reject_and_rerender`, missing evidence, or any other realism failure blocks approval. `eligible_for_human_review` is diagnostic clearance only and never approves the artifact by itself.
14. After the exact full raw is approved, enter ChatCut post-production using the material route chosen in step 3. Keep executing this step here; do not skip it or delete this ChatCut flow. The same package is also the standalone skill `数字人剪辑` — use that skill only when the user already has an approved raw and asks to edit it without restarting HeyGen generation. Read `references/chatcut-editing.md` and `references/chatcut-mg.md`; use `chatcut:chatcut-plugin-basics`, `chatcut:talking-head-guide`, `chatcut:create-motion-graphics`, `chatcut:asset-import`, `chatcut:transcription`, `chatcut:music`, `chatcut:export`, and `chatcut:verification`. Keep the approved raw unchanged as editable A-roll and perform spoken-content changes only through ChatCut Script. Finalize the Script edit, obvious-pause compression, and approximately 1.1x linked picture/audio pacing before any downstream layer, then write `chatcut-a-roll-report.json`. In `interactive`, stop at `awaiting_a_roll_approval` until the user explicitly approves that A-roll; in `auto`, run the locked A-roll auto-QA and continue only on a pass recorded with reviewer `auto-mode`. After the gate, add simplified-Chinese semantic captions; on the material route place only the approved transcript-grounded `material-plan.json` B-roll before planning MG; then add script-grounded MG on uncovered explanation beats, restrained flower text and speech-led sound effects, no-vocal BGM, voice ducking, `smooth_audio`, and complete QA. Never overlap B-roll, MG, or flower text on the same semantic span. Preserve identity, lip sync, voice, and performance in both routes.

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
- Write the motion block as a positive, present-tense description of a living person mid-conversation. Describe breathing, idle life, and motivated gestures first, and compress every prohibition into one short closing clause; a ban-dominated motion prompt reads as "hold still" and produces a frozen, waxy performance.
- Enforce the living idle floor: between gestures and during pauses, breathing stays visible at the chest and shoulders, the head keeps a barely visible one-to-two-degree drift with small resettles, and resting hands keep micro-relaxation. A freeze-frame idle is a stiffness defect, not restraint.
- Couple the channels: every head turn or nod rides on a slight neck-and-shoulder response absorbed by the torso — never turret-head rotation on a frozen body. Speech energy must reach the jaw, cheeks, nasolabial folds, and brows, with head and brow micro-accents landing on stressed syllables; reject lip-only articulation on a static face.
- Protect stability: keep gestures compact, unhurried, and forearm-led near the torso, and never let a hand stroke, a head accent, and a torso shift peak together. Facial geometry, eyewear, hairline, clothing, background, and framing must stay locked through motion — no warping, melting hands, crawling texture, or frame jitter.
- Make the performance imperfect on purpose: blink intervals must be uneven; allow occasional small saccades that return to the gaze anchor; on emphasis, let the brows lead and the head lag by about half a beat; insert a swallow or breath-style micro-pause at a few semantic boundaries; allow tiny torso weight shifts. Ban any motion that repeats on a fixed period.
- Use restrained hand gestures only when visible anatomy supports them. Complete one prepare-stroke-retract-cooldown cycle, then return hands to neutral before another gesture.
- Avoid repetitive swaying, continuous gesturing, mechanical face/head/hand synchrony, fused hands, or invented limbs.
- Derive faster/slower delivery, pauses, and emphasis from questions, warnings, contrasts, steps, explanations, and conclusions.
- Before any TTS call, create `voice-plan.json` from the current approved script. Vary provider-specific delivery by semantic beat, using amplified but controlled contrast for hooks, questions, warnings, reversals, and conclusions while keeping explanatory bridges distinctly restrained. MiniMax uses internal `director_intensity` translated into supported `emotion`, speed, emphasis, and post-segment pause; IndexTTS-2 uses the provider emotion vector and `emotion_intensity`. Cap either intensity scale at `0.85`.
- Preserve the approved text losslessly: concatenating every planned segment must reproduce the approved preview excerpt or full script byte-for-byte.
- Treat punctuation as the pause map. Never pause inside a complete Mandarin phrase merely to vary delivery; place pauses only at approved semantic boundaries.

Read `references/performance-profiles.md`, `references/performance-system.md`, and `references/realism.md` before building or validating the motion block.

## Batch and approval safety

Process batch jobs 严格串行 with `scripts/queue_jobs.py`. If the queue head waits for image, preview, or raw approval, stop all later jobs. Never execute two jobs concurrently or transfer approval evidence between jobs.

Voice-provider choice, material-route choice, image-model choice, image approval, preview approval, and raw approval are separate gates. Never transfer a voice, material, or image-model choice between jobs or infer it from earlier editing preferences, silence, or rights/spending consent. In interactive mode, ChatCut post-production may begin only after the exact full raw receives bound user approval. In auto mode, ChatCut may begin only after QA-passed raw approval bound to reviewer `auto-mode`.

## Local artifacts and recovery

`scripts/plan_job.py --dry-run` writes the seven compatible job files, including `heygen-app-plan.json`; its internal transport is `heygen-plugin-structured`. A plan is not evidence that a plugin call ran.

Use `scripts/update_job_state.py` for resumable v3 events and `scripts/migrate_job_state.py` for conservative v1/v2 migration. Reuse a recorded video ID after timeout. Retry only the failed stage; never submit a duplicate paid render to recover a poll or download.

Treat a failed public URL as a transport-stage failure. Reuse the approved local
artifact and its hash while repairing or replacing only the HTTPS path; do not
repeat MiniMax or IndexTTS-2 synthesis, image generation, avatar creation, or paid video
submission unless provider state proves that exact stage never succeeded.

## Required references

- Read `references/framework.md` for registry, state v3, queue, approvals, and recovery.
- Read `references/auto-mode.md` immediately after recording `operating_mode=auto` and before skipping any confirmation gate.
- Read `references/voice-routing.md` immediately after the per-job MiniMax/HeyGen/IndexTTS-2 choice and before narration resolution.
- Read `references/plugin-submission.md` before every live HeyGen submission.
- Read `references/checklists.md` at each gate.
- Read `references/performance-profiles.md` before visual/performance planning, and verify the private `business-human-123-v1` source against `references/performance-reference-123.json` before every live submission.
- Read `references/performance-system.md` after planning, after exact narration creation, and before every preview/full-raw approval.
- Read `references/realism.md` before image-prompt writing, motion-prompt writing, and every preview or raw QA pass.
- Read `references/api-facts.md` for current transport boundaries and volatile facts.
- Read `references/public-safety.md` when public distribution or disclosure matters.
- Read `references/brand-defaults.md` when resolving the fixed IP, distribution profile, original identity image, or a new job look.
- Read `references/view-modes.md` after choosing to generate a new boss look and before image or motion planning.
- Read `references/image-model-routing.md` immediately after the per-job OpenLux/Codex image-model choice and before any image call.
- Read `references/material-routing.md` immediately after an explicit yes to the company-material question and before drafting that job's script.
- Read `references/chatcut-mg.md` after bound full-raw approval and before ChatCut packaging or MG authoring.
- Read `references/chatcut-editing.md` immediately after bound full-raw approval and before the first ChatCut timeline edit.
- Keep this skill's ChatCut step 14 intact. The sibling skill `数字人剪辑` is the standalone entry for the same package on an already-approved raw.
