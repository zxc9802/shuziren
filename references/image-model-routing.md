# Image-model routing

Read this file immediately after the per-job OpenLux/Codex choice and before any image call. The **Candidate-image generation contract** and `references/realism.md` still apply on both routes.

## Per-job choice

After the user says yes to generating a new look and after `view_mode` / `selected_identity_master` are recorded, ask exactly:

**“这次生图使用 OpenLux，还是 Codex 内置模型？”**

Record `openlux` or `codex` only for this job. Never reuse an earlier answer. Never infer the route from realism complaints, cost talk, silence, or a previous job. Never silently fall back from one route to the other.

The job's authorization must cover sending the identity master to the selected provider before that call runs.

## Shared contract

Both routes must:

- generate exactly four labeled candidates in one round
- use the recorded `selected_identity_master` as the first and controlling person reference for every candidate
- send the exact master bytes; never substitute a generated candidate as another candidate's identity source
- keep four distinct gesture signatures
- request a vertical 9:16 seated medium close-up
- inspect photographic realism and side-view geometry before display

## `openlux`

Load credentials only from the skill-root `.env` or the process environment:

- `OPENLUX_API_KEY`
- `OPENLUX_BASE_URL` (default `https://api.openlux.ai/v1`)
- `OPENLUX_IMAGE_MODEL` (default `gpt-image-2-c`)

If the key or base URL is missing, stop with that blocker. Do not print the key. Do not write it into prompts, logs, registries, or deliverables.

Call `scripts/generate_openlux_candidates.py` with the identity-master path and a four-prompt JSON file. The script posts each candidate to `POST {OPENLUX_BASE_URL}/images/edits` with:

- `model`: `gpt-image-2-c`
- `image`: the exact `selected_identity_master` file
- `prompt`: that candidate's full prompt, including identity, view mode, realism, and its unique gesture signature
- `size`: `1024x1792` (9:16). If the provider rejects that size, retry the same prompt once with `1024x1536`; do not change the prompt or master.
- `quality`: `high`

Do not use text-only `/images/generations` for a boss look. That path has no identity master and is a failed identity-preserving call.

If OpenLux returns a transport, auth, or provider error, report the exact status and stop. Retry only the failed candidate after a corrected prompt or a recovered credential; do not regenerate the other three.

## `codex`

Use the Codex built-in image model. Attach the exact `selected_identity_master` file as the first reference image for every candidate. Do not call OpenLux. Do not omit the master.

## Outputs

Save the four artifacts as `1` through `4`, record each SHA-256, display the eligible candidates together, and wait for `采用第N张`.
