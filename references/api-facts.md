# HeyGen Transport Facts

Last reviewed: 2026-08-10.

## Active transport boundary

The active production path is the connected HeyGen plugin. Inspect `get_current_user` at runtime and use the subscription-credit source it reports. Do not describe plugin spend as browser-only plan credits.

`heygen-app-plan.json` remains the compatibility filename in job folders. Its required internal transport for new plans is `heygen-plugin-structured`; its action order uses a structured avatar/image creation tool once, persists the stable video ID, and polls that same ID.

Use `create_video_from_avatar` or `create_video_from_image` for an exact approved script. Do not use `video_agent_generate` when byte-for-byte narration is required. The only direct API/CLI bridge allowed is HeyGen v3 asset upload for an approved local image that the plugin cannot otherwise reference.

## Stable assets

- `voice1` identifies the authorized completed private cloned voice. A duplicated display name is not sufficient; verify the stable identity represented by the logged-in account.
- `image1` identifies the boss identity master and authorized private avatar group.
- 原始图片1 is the default job look.
- Approved generated looks remain children of the same identity group and receive task-derived names.

Do not invent remote IDs. Resolve the group with `get_avatar_group`, the fresh look with `list_avatar_looks`, and the voice with `get_voice`. If the plugin cannot locate or bind a registered private asset, stop with the precise missing/binding blocker.

## Structured plugin settings

The default raw contract is an Avatar IV-compatible look, portrait `9:16`, `720P`, fixed-camera motion direction, captions off, and the exact script with complete semantic voice/motion directions. The approved look and motion prompt must share the recorded `front`, `three_quarter_left_45`, or `three_quarter_right_45` view mode.

The plugin chooses the engine from avatar type, so verify `avatar_iv` in the look's supported engines instead of claiming an explicit engine selector. Verify the approved look evidence, exact voice ID, script hash, orientation, resolution, captions setting, and motion prompt before calling one structured generation tool once.

## Evidence classifier

Return only:

- `submitted`: the plugin acknowledges a stable video ID, but rendering is not yet proven;
- `blocked`: missing binding, unacknowledged ID, malformed state, or failed submission;
- `rendering`: `get_video` reports processing/generating or real nonzero progress for that ID;
- `completed`: `get_video` reports completed and exposes a real video resource.

Never trust a success-message string by itself. A plan, connector connection, chat statement, or visible draft is not a render.

## Volatile facts

Pricing, balances, plugin schemas, and supported avatar engines may change. Inspect the connected account and tool results at runtime. Never hard-code a historical balance, assume a credit source, or claim an unsupported payload field.
