# ChatCut Talking-Head Editing Stage

Use this reference only after the exact approved full raw is bound to the current job. It defines the editable ChatCut package shared with the standalone `数字人剪辑` skill. Keep HeyGen generation, the MiniMax narration, the approved identity, and the approved performance outside this stage.

## Stage contract

Run the package in dependency order:

`prepare -> a_roll_editing -> a_roll_review -> captions -> b_roll -> mg -> flower_text_and_sfx -> bgm -> final_qa`

- In `interactive`, `a_roll_review` becomes `awaiting_a_roll_approval`. Stop the current execution there and do not create captions, B-roll, MG, flower text, sound effects, or music until the user explicitly approves that A-roll.
- In `auto`, replace the human wait with `a_roll_auto_qa`. Continue only when the same A-roll evidence passes every check below; record reviewer `auto-mode`. Auto skips the human wait, not the gate or verification.
- Keep the global job in `post_production` while this ChatCut sub-stage is active. Record the current sub-stage and evidence in `chatcut-a-roll-report.json`; do not invent a new global production status that the state tools do not support.
- Any A-roll change after approval invalidates every downstream timing decision and the previous A-roll approval. Remove or rebuild dependent captions, B-roll, MG, sound effects, and music as needed, then pass the A-roll gate again.

## 1. Prepare

1. Target the intended ChatCut project and timeline; read their current tracks, items, and asset library before editing.
2. Bind the exact approved raw, approved script or explicit transcript-as-script instruction, `material_route`, and `operating_mode` for this job only.
3. Keep the raw as editable A-roll timeline items. Do not flatten the edit with local `ffmpeg`, clear unrelated tracks, overwrite user edits, or replace the approved identity, lip sync, voice, or performance.
4. Wait for the source transcript before transcript-driven editing. Treat current project state and the refreshed Script files as the source of truth.

## 2. A-roll editing

Use ChatCut Script for every spoken-content decision:

1. Call `read_script` and read the current `timeline.md` once for orientation.
2. When fixed hesitation sounds or batch silence cleanup is needed, run `clean_script` first. Use it for fixed fillers and mechanical pause compression only, not retakes, repeated sentences, or semantic decisions.
3. After `clean_script`, re-read the regenerated `timeline.md`. Remove only clear failed attempts, repeats, false starts, content-free head/tail space, and other defects while preserving complete ideas, connectors, necessary breaths, meaning, and narration order.
4. Apply the semantic edit with `apply_script`, then re-read the regenerated `timeline.md` and verify what the viewer will actually hear. Never cut spoken content with `find_transcript` plus `split_item` or `edit_item`.
5. Compress obvious long pauses rather than deleting all silence. A useful default is to compress pauses over about `0.8–1.0s` toward `0.3s`, while keeping normal sentence breaths and slightly longer rhetorical pauses.
6. Apply approximately `1.1x` to every kept A-roll item unless the user specified another rate. Change picture and its linked sound together; never speed only one side. Refresh project/timeline state after the speed change and use only the final post-speed timing downstream.
7. Run `smooth_audio` only after the whole timeline is final. If later structural edits reflow A-roll, run it again at the end.

Do not add any downstream layer during this stage.

## 3. A-roll evidence and gate

Write `chatcut-a-roll-report.json` before leaving A-roll. Record at least:

- project and timeline IDs;
- approved raw reference;
- duration before and after;
- applied playback speed;
- removed/compressed content summary and deliberately retained uncertain points;
- Script re-read result and full-listen result;
- sampled cut-point, first/last word, black-frame, pitch, and lip-sync checks;
- `review_status` and `reviewer`.

### Interactive

Set `review_status` to `awaiting_a_roll_approval`, report the result and duration, surface the editable ChatCut project for preview, and end the execution. Only an explicit reply such as “确认”, “A-Roll 可以”, or “继续做 B-Roll” approves it. Feedback, an error report, a new edit request, silence, or a generic “继续” without approving the A-roll does not. Apply the feedback, refresh the report, and wait again.

### Auto

Set reviewer to `auto-mode` and approve only when all are true:

- the refreshed Script preserves the approved meaning and order;
- no obvious repeat, failed attempt, content-free head/tail, or unintended long pause remains;
- no cut swallows a word, breaks a phrase, creates a black `[gap]`, or produces a hard audio pop;
- all kept A-roll items use the recorded speed and picture/audio remain synchronized;
- the first and last word, full duration, pitch, intelligibility, and sampled lip sync pass;
- the read-back project and timeline prove the intended items actually changed.

On any failure, record `review_status: failed`, preserve the exact blocker, and stop before captions or other downstream layers. On pass, record `review_status: approved` and reviewer `auto-mode`.

## 4. Captions

Create simplified-Chinese captions from the final post-speed timeline.

- Segment by complete short semantic phrases, normally one or two lines. Do not split product names, amounts, numbers plus units, or phrases such as “AI 剪辑 Agent”.
- Remove Chinese and English commas by default. Keep question marks, exclamation marks, full stops, numeric symbols, and other punctuation when they carry meaning.
- Use caption display controls for page breaks or merges. Never edit the transcript merely to repair caption layout.
- Verify proper nouns, numbers, English casing, entry/exit timing, safe area, and long-card wrapping.

## 5. B-roll and material

- On `material_route=none`, add no company B-roll. Keep the talking head and continue to MG.
- On `material_route=company`, follow only the approved `material-plan.json` and the user's explicit file-to-sentence mapping. Use the 1–2 relevant real asset categories and at most 1–2 approved supporting assets; do not substitute a plausible-looking file or fill the timeline with unrelated material.
- Preserve A-roll sound. Mute or omit B-roll source audio unless the user explicitly requested it.
- Enter on the grounded keyword and leave when that explanation ends. Do not cut away in the first or last three seconds unless requested.
- Inspect every source before choosing `cover` or `contain`. Protect readable UI, titles, logos, products, and the caption band, then verify the composed frame.

Place material before planning MG so `mg-plan.json` can exclude already-covered spans.

## 6. MG and flower text

Read `references/chatcut-mg.md`. Write `mg-plan.json` from the approved script and the final post-speed transcript, then place script-grounded MG only on explanation beats that do not already contain B-roll or supporting material.

Add restrained business-tech flower text only on remaining beats with no MG or material cover. Keep the face, mouth, glasses, hands, product UI, and caption band clear.

## 7. Restrained speech-led sound effects

Use light `whoosh`, `pop`, `click`, `hit`, `cash`, or `riser` accents only when they serve a hook, viewpoint landing, amount, reversal, material entrance, MG reveal, or important transition.

- Do not add an effect to every sentence or stack similar effects.
- Keep each effect short and below the speech. Check its peak against the exact word and visual event.
- Put short effects on a track without `follower` unless the user explicitly wants them ducked.
- If no suitable authorized effect exists in the project or supported source, skip that effect rather than inventing an unrelated sound.

## 8. Background music and final audio

Use one modern, light, no-vocal bed that matches the subject without competing with speech. Fit it from frame zero to the real content end, add a natural fade, set speech to `anchor` and music to `follower`, and let ChatCut duck music under the voice. Do not pre-duck the clip heavily and also deepen `duckDepthDb` unless requested.

After all structural and audio placements are final, run `smooth_audio`. Listen through the full timeline and verify voice clarity, cut smoothness, effect peaks, music coverage, fades, and absence of clipping or abrupt silence.

## 9. Error and delivery boundaries

- A stale Script state or `apply_script` markdown error may be refreshed, corrected, and retried once. Do not silently loop.
- Missing or ambiguous assets, locked-track conflicts, access/upload denial, offline media, unresolved overlap, or uncertain visual/audio proof stops the current stage. Preserve existing edits and report the exact blocker; never skip ahead.
- Keep the live editable ChatCut project as the review surface.
- In the full `数字人` end-to-end job, the requested final packaged video authorizes export after final QA. In standalone `数字人剪辑`, export only when the user explicitly requests render, download, export, or final-file delivery.

Final QA must cover project structure, timeline gaps/overlaps, captions, B-roll mapping, MG and flower-text conflicts, sound-effect synchronization, music/ducking, representative composed frames, complete playback, and the exported file when export is authorized. Do not describe unverified work as complete.
