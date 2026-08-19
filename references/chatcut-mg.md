# ChatCut Script-Grounded MG

Use this reference after bound full-raw approval, final A-roll timing, the A-roll approval/auto-QA gate, captions, and any approved material placement. MG is part of the standard ChatCut package for every job, including auto mode on the no-material route. It is not an additional per-job confirmation gate.

Read `chatcut:talking-head-guide` and `chatcut:create-motion-graphics` before authoring. Do not load the paid generator-only `motion-graphic-gen` path when the connected ChatCut surface uses direct-authored JSX.

## Purpose

During explanation beats, add restrained Motion Graphics that visualize what the approved script is actually saying. The talking head remains the base. MG supports comprehension; it does not replace the approved raw, rewrite the narration, or invent a second story.

## When to add an MG

Add an MG only where a visual layer helps the viewer grasp a point that speech alone is easy to miss:

- a definition or named concept;
- a numbered or sequenced set of steps;
- a contrast, reversal, warning, or before/after;
- a short list, comparison, or process;
- a hook claim or closing conclusion worth holding on screen.

Do not add an MG on every sentence, on ordinary connective bridges, or as decoration that only repeats the caption. Prefer **3–6 MGs** on an approximately 60–90 second video. A shorter video may use fewer. Never exceed one MG per distinct semantic beat.

Default to a transparent overlay that keeps the speaker visible. Use one opaque full-screen beat only when the information is too dense for a safe overlay, such as a multi-step list or comparison. A second full-screen beat is allowed only for a second, different dense structure.

## Script grounding

Every MG must be grounded in one approved narration sentence or one complete semantic unit.

- On-screen words must be a lossless excerpt or a shorter verbatim fragment of the approved script. Do not paraphrase into a new claim.
- Do not invent a customer, metric, result, product name, feature, or screenshot the script does not state.
- Do not use company B-roll, fake UI, or a generated still as a substitute for MG, and do not use MG as a substitute for a required real company asset on the material route.
- If the sentence is only atmosphere or a handoff, skip MG and keep the talking head.

Write `mg-plan.json` after A-roll approval/auto-QA, captions, and any material placement are in place, before creating MG assets. Each entry records:

- exact narration sentence;
- transcript start and end;
- viewer job (`definition`, `steps`, `contrast`, `list`, `hook`, or `conclusion`);
- form (`lower-third`, `side-list`, `pull-quote`, or `full-screen-beat`);
- background (`transparent` or `opaque`);
- on-screen text copied from the approved script;
- face-safe and caption-safe placement;
- duration and exit when the beat ends;
- conflict check against B-roll and flower text.

The planned spans must use word-level transcript timestamps from the post-A-roll timeline. An MG lands at the start of its grounded sentence and exits when that explanation ends.

## Placement and protection

- Protect the face, head, hair, glasses, mouth, chin, visible hands, and any product UI.
- Keep the caption band clear. On portrait `1080×1920`, bottom overlays use about `bottom: 576` unless a screenshot proves a safer rectangle.
- Do not cover essential subtitles or flower text. If a beat already has flower text, either skip MG or use a side form that does not compete.
- On the material route, do not overlap an MG with a company B-roll or supporting still on the same span. If that sentence already has real material, skip MG unless a tiny label can sit in empty space without covering the product UI.
- Prefer side or lower-third overlays. Do not default chapter titles or quotes to the top corners.
- Verify settled frames after the first MG before creating the rest. A successful asset mutation is not visual proof.

## Visual language

Use one restrained business-tech family for the whole video: cool neutrals, one accent, readable sans type, low visual density, and short motion. Match the existing flower-text tone. Do not switch styles mid-video.

- Overlays use a natural-box asset, not a full-canvas sticker.
- Motion is short: appear with the speech beat, hold to be read, exit when the point is made. No looping decoration, no constant particle fields, no cinematic camera moves.
- Keep numbers, labels, and list items editable properties when the ChatCut surface supports them.
- In interactive mode, apply this locked package without asking whether to add MG. After the first placed MG, continue unless the user stops or asks for a style change. Do not open a new FIFO-blocking approval state.
- In auto mode, apply the same package with no style picker.

## Order inside ChatCut

1. Import the approved raw and wait for transcription.
2. Follow `references/chatcut-editing.md`: finalize A-roll through Script, apply approximately 1.1x linked picture/audio pacing, write `chatcut-a-roll-report.json`, and pass the interactive or auto gate.
3. Apply dynamic captions so the caption band is known.
4. On the material route, place approved `material-plan.json` assets first.
5. Write `mg-plan.json`, exclude material-covered spans, and place the planned MGs on the final post-speed timeline.
6. Add restrained business-tech flower text and speech-led sound effects on remaining eligible beats.
7. Fit original no-vocal BGM, set speech `anchor` and music `follower`, then run `smooth_audio`.
8. Run project-structure, timeline, caption, audio, visual, full-export, and final-media QA.

Preserve the approved raw, identity, lip sync, voice, and performance through every layer.
