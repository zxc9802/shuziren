# HeyGen Plugin Submission

Read this reference immediately before every live preview or full-raw submission.

## Transport

Use the connected HeyGen plugin. Inspect the account with `get_current_user`
and use its reported subscription-credit source. Do not hard-code a balance or
claim that plugin spend uses browser-only plan credits.

Read the recorded narration provider before building any payload. On `minimax`,
upload and bind the exact MiniMax audio; HeyGen must not re-synthesize it. On
`heygen`, submit the verbatim script with verified HeyGen `voice1`.

Use `create_video_from_avatar` when the approved look has a ready look ID. Use
`create_video_from_image` only when the exact approved image is represented by
an asset ID. Do not use `video_agent_generate` for an approved verbatim script;
Video Agent may treat the script as a concept and rewrite it.

## Exact look and narration

1. Resolve `image1` with `get_avatar_group` and `list_avatar_looks`.
2. Match the approved look by stable group membership and approved artifact
   evidence. Never substitute another look because it has a similar name.
3. Require `status=completed`, a non-null preview image, portrait orientation,
   and `avatar_iv` in `supported_api_engines`.
4. Verify the approved look itself matches the recorded `view_mode`. A motion
   prompt cannot turn a frontal source into an approved 45° source look.
5. When the approved image is local-only, verify its SHA-256, upload only that
   file through the HeyGen v3 asset endpoint bridge, then call
   `create_photo_avatar` with the existing `image1` group ID. Poll until the
   resulting look is ready and resolve its fresh look ID.
6. On `minimax`, verify `huangxu1`, the local audio SHA-256,
   and the uploaded HeyGen audio asset ID. On `heygen`, resolve HeyGen `voice1`
   with `get_voice`; require the exact stable voice ID and expected language.
   A matching display name is insufficient.

## Narration safety

On `minimax`, submit the exact MiniMax audio as the driving audio. HeyGen must not re-synthesize,
paraphrase, translate, or rewrite it. Do not also pass a HeyGen voice ID or a script field that
could trigger a second narration. On `heygen`, submit the approved plain-text script with the
exact HeyGen `voice1` ID. For `create_video_from_avatar` and `create_video_from_image`, omit
`voiceSettings` by default. Add a video-tool voice setting only when the current connector
schema documents that exact field and a same-voice preview through the same video endpoint has
already proved clear Mandarin, stable identity, and an expected duration. Do not copy parameters
from `create_speech` into a video-generation call; the endpoint schemas and credit paths are
independent.

After download, listen to the complete preview in addition to checking media streams. If the
speech is unintelligible, does not read the approved text, changes the selected voice identity, or
materially exceeds the expected or previous baseline duration, fail voice QA. Do not approve
that artifact for full-raw generation even when the picture looks acceptable.

## Structured payload

Pass and verify:

- the approved script or approved opening-preview excerpt verbatim on `heygen`;
- exact HeyGen `voice1` ID on `heygen`;
- exact MiniMax audio asset ID and bound local SHA-256 on `minimax`;
- complete view-mode-aware motion prompt;
- portrait `9:16`;
- `720P`;
- captions off;
- one submission only.

Reject any payload containing both a MiniMax driving-audio asset and a HeyGen narration voice.
Never silently fall back to the unselected provider.

The plugin chooses the engine from avatar type. Do not claim an explicit engine
selection; verify Avatar IV compatibility from look metadata before spend.

For a requested preview, use a character-preserving opening excerpt targeting
15 seconds. Measure the downloaded result. Report the actual duration and claim
"exact 15 seconds" only when media QA verifies 15.0 seconds.

## Submission and recovery

Re-read the payload immediately before spend. Call exactly one structured
generation tool once. Persist the returned video ID immediately.

Use `get_video` to poll that ID. A success sentence is not evidence. An
acknowledged ID may be reported as submitted. Report rendering only when the
provider status or progress proves it, and completed only when a real video URL
and completed status exist.

On timeout, continue polling the recorded ID. On an expired download URL, fetch
the same result again. Never create another paid render to recover polling or a
download.
