# HeyGen Browser Submission

Read this reference immediately before every live preview or full-raw submission.

## Control strategy

Use accessibility role, accessible name, and 可见标签 to locate controls. Re-inspect the current page after every navigation or major state change. Do not depend on hard-coded CSS selectors, screen coordinates, stale node IDs, or remembered layout.

Operate the page yourself. Do not ask the user to manually select an avatar/voice or click Generate. If a control cannot be identified or a private asset cannot be safely bound, stop and report the 精确阻塞原因, the last verified page state, and the missing control or asset.

## Exact look and voice

1. Open the authenticated paid HeyGen workspace represented by the current job.
2. Select 原始图片1 when the job records `original_image1`; otherwise upload/select the exact generated artifact whose SHA-256 was approved.
3. Verify the chosen avatar 缩略图 is visible in the bound presenter slot and belongs to the expected `image1` identity group.
4. Bind `voice1`. Verify its stable identity or account asset record, not only a duplicated display name.
5. Never accept a blank presenter tile, generic office background, unresolved blueprint, or a prompt telling the user to choose the avatar later.

## Exact script and settings

Paste the submitted script verbatim. Compare normalized visible text with the source before spend; normalization may standardize line endings but may not rewrite, translate, summarize, add a title, or remove punctuation/text.

Set and verify:

- engine: Avatar IV;
- orientation: portrait `9:16`;
- resolution: `720P`;
- camera: fixed/locked;
- captions: off;
- music: off;
- B-roll: off;
- transitions/camera motion: off;
- image candidate count: one maximum.

Confirm the complete script is covered by the expected voice duration. Reject truncated text, unexpected silence, or a duration derived from a summary instead of the source.

## Voice and motion prompt

Preserve the entire voice direction so semantic beats can be faster/slower with appropriate pauses and emphasis. Do not collapse the delivery to one global constant speed.

Preserve the complete 动作提示:

- fixed camera and fixed framing;
- direct gaze, natural irregular blinks, subtle micro-expressions, calm breathing;
- small phrase-led head movement that returns to center;
- stable shoulders and torso;
- restrained topology-safe hand gestures;
- one complete prepare-stroke-retract-cooldown gesture, then neutral;
- no repetitive swaying, continuous gesturing, zoom, cuts, or invented limbs.

Re-open or expand any UI field necessary to verify that the full text remains present after page updates.

## Spend and post-click verification

Perform a final visible comparison of avatar, voice, exact script, duration, Avatar IV, `9:16`, `720P`, disabled extras, locked camera, and full motion prompt. If any field fails, stop before spend.

点击一次 Generate. Do not click again while the page is thinking, generating, rendering, processing, or polling.

Immediately capture the post-click state and classify it:

- `blueprint_ready`: `thinking`, `progress=0`, blueprint/draft, or no video;
- `blocked`: avatar unbound, Generate still visibly available for an unsubmitted job, malformed result, or failed submission;
- `rendering`: stable video ID, bound avatar, video resource, progress above zero, at least one video, Generate hidden/disabled;
- `completed`: real-video evidence plus completed status/full progress.

Only `rendering` or `completed` permits reporting that generation started. A connector message, assistant statement, plan card, or “successfully configured” text is not evidence.

## Recovery

Persist the stable video ID immediately. Poll that existing ID. If polling times out or a download URL expires, resume polling/fetching; do not resubmit. If the page loses state before a stable video ID is visible, stop and report the exact evidence available rather than clicking Generate again.
