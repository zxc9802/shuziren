# HeyGen Plan-Credit Digital Human Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the reusable digital-human production Skill so voice cloning, speech synthesis, avatar identity, and Avatar IV raw video all use the authenticated HeyGen App and the user's plan credits, with no MiniMax, API keys, CLI transport, or direct HTTP.

**Architecture:** Keep the deterministic content, voice, visual, and performance directors. Replace the provider layer with a strict HeyGen App registry plus network-free App action plans: one-time `clone_voice`, one-shot SSML `create_speech`, runtime avatar-look resolution, and `create_video_from_avatar`. Preserve the resumable state machine and bind HyperFrames access to explicit approval of the exact QA-passed full raw artifact.

**Tech Stack:** Python 3 standard library, `unittest`, HeyGen Codex App OAuth tools, HeyGen Avatar IV, HyperFrames plugin, Markdown/YAML Skill metadata.

---

## File map

- `scripts/dhflow/registry.py`: trusted HeyGen voice/avatar registry v2 and alias resolution.
- `scripts/init_asset_registry.py`: create a v2 registry from completed HeyGen IDs and local authorized sources.
- `scripts/dhflow/heygen_app.py`: SSML and network-free HeyGen App action-plan construction.
- `scripts/dhflow/planner.py`: assemble directors plus the App action plan.
- `scripts/plan_job.py`: atomically emit planning artifacts and a fresh v2 state.
- `scripts/dhflow/state.py`: HeyGen-only state, migration, idempotency, and bound full-raw approval.
- `scripts/update_job_state.py`: safely record App results and user approval without hand-editing JSON.
- `SKILL.md`, `README.md`, `agents/openai.yaml`, `references/*`: final orchestration contract.
- `tests/test_registry.py`, `tests/test_heygen_app.py`, `tests/test_planner.py`, `tests/test_state.py`: offline coverage; no provider calls.
- Delete `scripts/dhflow/payloads.py` and `tests/test_payloads.py` after replacement tests pass.

---

### Task 1: Finish and checkpoint the bound raw-approval gate

**Files:**
- Modify: `scripts/dhflow/state.py`
- Modify: `scripts/init_asset_registry.py`
- Modify: `tests/test_state.py`
- Modify: `tests/test_registry.py`

- [ ] **Step 1: Inspect the interrupted work without discarding it**

Run:

```powershell
git diff -- scripts/dhflow/state.py scripts/init_asset_registry.py tests/test_state.py tests/test_registry.py
```

Expected: pending tests require a full raw artifact, SHA-256 match, strict QA, reviewer, timestamp, evidence reference, and HeyGen video ID; UTF-8 subprocess capture is explicit.

- [ ] **Step 2: Run the focused tests**

```powershell
python -X utf8 -m unittest tests.test_state tests.test_registry -v
```

Expected: all focused tests pass; a bare `approval.raw=true`, preview artifact, mismatched hash, missing reviewer, or missing HeyGen video ID is rejected.

- [ ] **Step 3: Add any missing positive helper test**

If not already present, add this assertion to `tests/test_state.py`:

```python
def test_bound_full_raw_approval_is_the_only_postproduction_path(self):
    state = approved_full_raw_state()
    advanced = transition(state, "post_production")
    self.assertEqual("post_production", advanced["status"])
    self.assertEqual(state["artifacts"]["raw_video"]["sha256"], advanced["approval"]["raw_artifact_sha256"])
```

- [ ] **Step 4: Verify default Windows output is clean**

```powershell
Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
python -m unittest tests.test_state tests.test_registry -v
```

Expected: PASS with no background `UnicodeDecodeError`.

- [ ] **Step 5: Commit only the approval/encoding files**

```powershell
git add scripts/dhflow/state.py scripts/init_asset_registry.py tests/test_state.py tests/test_registry.py
git diff --cached --check
git commit -m "fix: bind post-production to approved raw artifact"
```

---

### Task 2: Replace the MiniMax registry with HeyGen App assets

**Files:**
- Modify: `scripts/dhflow/registry.py`
- Modify: `scripts/init_asset_registry.py`
- Modify: `tests/test_registry.py`
- Modify: `tests/test_planner.py` (test fixtures only, to keep the suite green after the intentional registry-v2 break)

- [ ] **Step 1: Write failing registry-v2 tests**

Add tests equivalent to:

```python
def test_resolves_ready_heygen_voice_and_avatar(self):
    registry = {
        "version": 2,
        "defaults": {"voice": "voice1", "identity": "image1"},
        "voices": {"voice1": {
            "provider": "heygen-app", "voice_id": "voice_abc123",
            "clone_status": "complete", "language": "zh",
            "speech_compatible": True, "source": "inputs/voice.mp3",
            "source_sha256": "a" * 64, "authorized": True,
            "persona": "professional-trustworthy-business",
        }},
        "identities": {"image1": {
            "provider": "heygen-app", "avatar_group_id": "group_abc123",
            "source": "inputs/portrait.png", "source_sha256": "b" * 64,
            "authorized": True, "persona": "professional-trustworthy-business",
            "performance_profile": "business-human-1", "hand_topology": "separated",
        }},
    }
    assets = resolve_assets(registry)
    self.assertEqual("voice_abc123", assets["voice"]["voice_id"])
    self.assertEqual("group_abc123", assets["identity"]["avatar_group_id"])
```

Also test rejection of provider `minimax-cn`, `provider_voice_id`, incomplete clone status, `speech_compatible != True`, missing hashes, unauthorized aliases, URL-shaped IDs, and unknown fields.

- [ ] **Step 2: Verify RED**

```powershell
python -X utf8 -m unittest tests.test_registry -v
```

Expected: FAIL because the current schema is version 1 and requires MiniMax fields.

- [ ] **Step 3: Implement the v2 registry**

Use these exact public signatures: `write_registry(path, voice_id, avatar_group_id, voice_source, image_source, authorized, *, exclusive=False)` and `resolve_assets(registry, *, voice_alias=None, identity_alias=None)`.

`write_registry` must hash existing source files with SHA-256, write `provider="heygen-app"`, `clone_status="complete"`, `language="zh"`, and `speech_compatible=True`, validate before writing, and never include credentials or URLs.

- [ ] **Step 4: Update the CLI arguments**

`scripts/init_asset_registry.py` must expose:

```text
--voice-id
--avatar-group-id
--voice-source
--image-source
--authorized
--force
```

It must reject missing local sources, hash them, and preserve exclusive creation.

- [ ] **Step 5: Verify GREEN**

```powershell
python -X utf8 -m unittest tests.test_registry -v
python -X utf8 -m unittest tests.test_planner -v
python scripts/init_asset_registry.py --help
```

Expected: all tests pass; planner fixtures use the exact registry-v2 schema without changing production planner behavior; help contains `--avatar-group-id`; emitted JSON contains no MiniMax or API-key fields.

- [ ] **Step 6: Commit**

```powershell
git add scripts/dhflow/registry.py scripts/init_asset_registry.py tests/test_registry.py tests/test_planner.py
git diff --cached --check
git commit -m "feat: register HeyGen app voice and avatar assets"
```

---

### Task 3: Build HeyGen SSML and App action plans

**Files:**
- Create: `scripts/dhflow/heygen_app.py`
- Create: `tests/test_heygen_app.py`
- Delete after GREEN: `scripts/dhflow/payloads.py`
- Delete after GREEN: `tests/test_payloads.py`

- [ ] **Step 1: Write failing action-plan tests**

```python
from scripts.dhflow.heygen_app import build_app_action_plan, build_speech_ssml

def test_ssml_preserves_text_and_varies_delivery(self):
    voice_plan = {"segments": [
        {"id": "s1", "text": "为什么现在开始？", "delivery": {"speed": "measured", "emotion": "calm", "pause_after": "medium", "emphasis": "question_core"}},
        {"id": "s2", "text": "先解决一个问题。", "delivery": {"speed": "brisk", "emotion": "calm", "pause_after": None, "emphasis": "action"}},
    ]}
    ssml = build_speech_ssml(voice_plan)
    self.assertIn('<prosody rate="96%">', ssml)
    self.assertIn('<prosody rate="105%">', ssml)
    self.assertEqual("为什么现在开始？先解决一个问题。", strip_ssml(ssml))

def test_plan_uses_only_heygen_app_tools(self):
    plan = build_app_action_plan(voice_plan, visual_plan, performance_plan, "voice_abc", "group_abc")
    self.assertEqual("heygen-app-oauth", plan["transport"])
    self.assertEqual("mcp__codex_apps__heygen_create_speech", plan["speech"]["tool"])
    self.assertEqual("mcp__codex_apps__heygen_create_video_from_avatar", plan["video"]["tool"])
    self.assertNotIn("http", json.dumps(plan).lower())
    self.assertNotIn("api_key", json.dumps(plan).lower())
```

Add cases for XML escaping, punctuation, Unicode, invalid delivery values, exact text reconstruction, topology-specific prompts, no hands/arms for `not_visible`, no absolute timestamps, and no script text inside the motion prompt.

- [ ] **Step 2: Verify RED**

```powershell
python -X utf8 -m unittest tests.test_heygen_app -v
```

Expected: `ModuleNotFoundError` for `scripts.dhflow.heygen_app`.

- [ ] **Step 3: Implement the network-free adapter**

Public interface:

```python
HEYGEN_APP_TRANSPORT = "heygen-app-oauth"

def build_speech_ssml(voice_plan: dict) -> str:
    """Return one escaped <speak> document with relative prosody and breaks."""

def build_app_action_plan(voice_plan, visual_plan, performance_plan, voice_id, avatar_group_id) -> dict:
    """Return JSON-safe App tool names and non-secret arguments/templates only."""
```

Use a private immutable speed mapping such as `deliberate=92%`, `measured=96%`, `natural=100%`, `brisk=105%`. The speech action uses `inputType="ssml"`, `language="zh"`, and the trusted `voiceId`. Before speech, paginate all private Starfish voices through `data[].voice_id`, `has_more`, and `next_token` using the exact next `token` input, then require the selected voice ID to be present. Paginate private avatar looks the same way and select one `data[]` item with matching `group_id`, `status="completed"`, `image_height > image_width`, and a stable `id` tie-break. Resolve that `id` with `get_avatar_look`, recheck the same ID/group/status/dimensions, inspect `supported_api_engines` without treating Avatar IV membership as a documented requirement, and use the connector's photo-avatar default contract (`avatar_iv`). Bind exactly `data.preview_image_url` ephemerally into local Frame Check with the validated identity, wardrobe, background, pose, framing, mouth visibility, safe areas, image-QA requirements, optional scene/lighting/props/platform intent, 9:16, 720p, and hand topology. The video action stores `avatarGroupId` for runtime look resolution and an ephemeral runtime binding whose real target argument is `audioUrl`, sourced from the preceding speech result with `persist=false`; the plan must never store the returned URL value. Include account check, voice readiness and membership, deterministic look discovery and verification, Frame Check, speech, video create, and polling actions in order.

- [ ] **Step 4: Remove direct provider payload code**

Delete `payloads.py` and `test_payloads.py` only after `test_heygen_app` passes. Confirm no other module imports them:

```powershell
rg -n "payloads|MINIMAX_|api\.minimaxi|api\.heygen\.com" scripts/dhflow/heygen_app.py tests/test_heygen_app.py scripts/dhflow/planner.py
rg -n "_MINIMAX_CLONE_VOICE_ID|minimax" scripts/dhflow/state.py tests/test_state.py
```

Expected: zero matches in the new App adapter and planner. The second command records the known legacy state-migration dependency; Task 5 must remove it together with tests proving old MiniMax IDs are never relabeled as HeyGen IDs. The final Task 8 production scan still requires zero stale routes.

- [ ] **Step 5: Verify GREEN and strict JSON**

```powershell
python -X utf8 -m unittest tests.test_heygen_app -v
python -X utf8 -m unittest discover -s tests -v
```

Expected: all tests pass and every action plan serializes with `allow_nan=False`.

- [ ] **Step 6: Commit**

```powershell
git add scripts/dhflow/heygen_app.py tests/test_heygen_app.py scripts/dhflow/payloads.py tests/test_payloads.py
git diff --cached --check
git commit -m "feat: plan HeyGen app speech and avatar actions"
```

---

### Task 4: Integrate the App plan into the deterministic job CLI

**Files:**
- Modify: `scripts/dhflow/planner.py`
- Modify: `scripts/plan_job.py`
- Modify: `tests/test_planner.py`

- [ ] **Step 1: Write failing planner integration tests**

```python
def test_job_uses_heygen_assets_and_app_actions(self):
    plan = build_job_plan(script, heygen_registry(), {})
    self.assertEqual("voice1", plan["task"]["voice_alias"])
    self.assertEqual("image1", plan["task"]["identity_alias"])
    self.assertEqual("heygen-app-oauth", plan["heygen_app_plan"]["transport"])
    self.assertNotIn("minimax", json.dumps(plan).lower())

```

The CLI test must invoke `scripts/plan_job.py` in a temporary directory with a valid registry-v2 fixture, assert a zero exit code, assert the exact seven-file set below, and validate the parsed `state.json` with `validate_state`:

```python
{
    "task.json", "content-beats.json", "voice-plan.json", "visual-plan.json",
    "performance-plan.json", "heygen-app-plan.json", "state.json",
}
```

- [ ] **Step 2: Verify RED**

```powershell
python -X utf8 -m unittest tests.test_planner -v
```

Expected: FAIL because the planner still expects `provider_voice_id` and emits no App plan.

- [ ] **Step 3: Implement planner integration**

Use `assets["voice"]["voice_id"]` and `assets["identity"]["avatar_group_id"]`. Add `heygen_app_plan` to the returned plan. Keep `preview_choice="pending"`, default `9:16`, default raw review `720p`, exact script preservation, trusted alias selection, and the strict override allowlist.

- [ ] **Step 4: Emit the seventh artifact atomically**

Add:

```python
"heygen-app-plan.json": "heygen_app_plan"
```

to `ARTIFACTS`. A failed validation must leave no output directory.

- [ ] **Step 5: Verify GREEN**

```powershell
python -X utf8 -m unittest tests.test_planner -v
python scripts/plan_job.py --help
```

Expected: tests pass; a temp dry-run writes exactly seven files and no network activity occurs.

- [ ] **Step 6: Commit**

```powershell
git add scripts/dhflow/planner.py scripts/plan_job.py tests/test_planner.py
git diff --cached --check
git commit -m "feat: emit HeyGen app job plans"
```

---

### Task 5: Make state and result recording HeyGen-only and resumable

**Files:**
- Modify: `scripts/dhflow/state.py`
- Create: `scripts/update_job_state.py`
- Modify: `scripts/init_job_state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write failing HeyGen-only state tests**

```python
def test_migration_never_relabels_minimax_voice_as_heygen(self):
    migrated = migrate_v1({
        "version": 1,
        "status": "planned",
        "minimax": {"voice_id": "OldMiniMax01"},
    })
    self.assertNotIn("voice_id", migrated.get("assets", {}).get("voice", {}))
    self.assertEqual("assets_ready", STATES[3])

def test_records_reusable_heygen_results_without_urls(self):
    state = create_state(status="assets_ready")
    state = record_audio_ready(state, audio_id="audio_123", content_sha256="a" * 64, duration_seconds=42.5)
    self.assertEqual("audio_ready", state["status"])
    self.assertNotIn("url", json.dumps(state).lower())
```

Also test voice clone ID, avatar group ID, runtime look ID, video ID, duplicate/idempotent events, conflicting IDs, invalid transitions, and bound raw approval.

- [ ] **Step 2: Verify RED**

```powershell
python -X utf8 -m unittest tests.test_state -v
```

Expected: FAIL because states still contain `image_ready` and MiniMax migration.

- [ ] **Step 3: Implement the HeyGen-only state sequence**

Use:

```python
STATES = (
    "created", "planned", "preview_choice_recorded", "assets_ready",
    "audio_ready", "raw_rendering", "raw_qa", "awaiting_raw_approval",
    "post_production", "final_qa", "complete",
)
```

Add pure non-mutating record helpers for ready assets, audio, raw video, and raw approval. Store only stable IDs, hashes, duration, QA, and evidence; never signed URLs or headers.

- [ ] **Step 4: Add the atomic update CLI**

`scripts/update_job_state.py` must read strict UTF-8/BOM JSON, support explicit subcommands/events, write via temp file plus `os.replace`, refuse unknown fields, and make an exact-byte backup before destructive migration. It must not call HeyGen.

- [ ] **Step 5: Verify GREEN and migration safety**

```powershell
python -X utf8 -m unittest tests.test_state -v
python scripts/update_job_state.py --help
```

Expected: PASS; MiniMax IDs are not accepted as HeyGen voice IDs; old files remain externally preserved.

- [ ] **Step 6: Commit**

```powershell
git add scripts/dhflow/state.py scripts/update_job_state.py tests/test_state.py
git diff --cached --check
git commit -m "feat: track resumable HeyGen app production"
```

---

### Task 6: Rewrite the complete Skill for HeyGen plan credits

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `agents/openai.yaml`
- Modify: `references/framework.md`
- Modify: `references/checklists.md`
- Modify: `references/api-facts.md`
- Modify: `references/performance-profiles.md`

- [ ] **Step 1: Record the provider-switch behavior baseline**

Append a deterministic contract audit to `D:\数字人智能体\work\skill-baseline.md` showing current failures: MiniMax references, API keys, CLI fallback, direct payloads, no HeyGen clone/speech App sequence, and incorrect artifact/state names.

- [ ] **Step 2: Rewrite the main Skill contract**

The required live order must be exactly:

```text
authorization + HeyGen App account check
-> trusted voice/avatar registry
-> plan_job dry-run
-> ask optional 15-second preview
-> reuse or clone selected HeyGen voice
-> resolve selected HeyGen avatar group/look
-> HeyGen App SSML speech
-> HeyGen App Avatar IV full raw
-> automatic raw QA
-> explicit bound approval of exact full raw
-> HyperFrames packaging
-> final QA and archive
```

State that live transport is HeyGen App OAuth only. Forbid MiniMax, API keys, CLI fallback, and direct HTTP. Keep `allow_implicit_invocation: false`.

- [ ] **Step 3: Make references implementation-accurate**

`framework.md` documents seven dry-run artifacts, HeyGen registry v2, account/credit gate, App tools, v3 state, external legacy preservation, and recovery. `checklists.md` separates account/authorization, voice clone readiness, avatar readiness, speech QA, raw QA, raw approval, HyperFrames QA, and final QA. `api-facts.md` becomes an App-capability record and contains no live endpoint instructions. `performance-profiles.md` preserves semantic motion and topology downgrade.

- [ ] **Step 4: Remove stale README routes**

The README must contain zero matches for:

```text
MiniMax
MINIMAX_API_KEY
HEYGEN_API_KEY
api.heygen.com
heygen CLI
provider_voice_id
```

It must explain that local photo onboarding may require a one-time manual HeyGen web/App upload when no existing private avatar can be reused.

- [ ] **Step 5: Validate behavior**

```powershell
python -X utf8 C:\Users\78575\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -X utf8 -m unittest discover -s tests -v
rg -n "MiniMax|MINIMAX_API_KEY|HEYGEN_API_KEY|api\.heygen\.com" SKILL.md README.md agents references scripts
```

Expected: Skill valid; tests pass; the stale-route scan has no production matches.

- [ ] **Step 6: Commit**

```powershell
git add SKILL.md README.md agents/openai.yaml references
git diff --cached --check
git commit -m "feat: orchestrate HeyGen plan-credit production"
```

---

### Task 7: Bootstrap a network-free workspace dry run

**Files:**
- Create: `D:\数字人智能体\assets\registry.example.json`
- Create: `D:\数字人智能体\work\jobs\heygen-framework-dry-run\*`
- Preserve: `D:\数字人智能体\work\job-state.json`

- [ ] **Step 1: Create a non-live example registry**

Use explicit non-secret fixture IDs marked as examples. Do not claim they are usable HeyGen resources. The real registry is created only after read-only account discovery and explicit selection/clone confirmation.

- [ ] **Step 2: Run asset preflight**

```powershell
python scripts/preflight_assets.py --script tests/fixtures/question-warning.md --portrait D:\老板图片.png --voice D:\老板音频.mp3
```

If the actual portrait path differs, use the user-provided path already present in the workspace. Do not fabricate duration if `ffprobe` is unavailable.

- [ ] **Step 3: Generate a complete dry-run job**

```powershell
python scripts/plan_job.py --script tests/fixtures/question-warning.md --registry D:\数字人智能体\assets\registry.example.json --out D:\数字人智能体\work\jobs\heygen-framework-dry-run --dry-run
```

Expected: seven JSON files, no network call, HeyGen App tool names, variable speech prosody, semantic actions, no credentials/endpoints/MiniMax.

- [ ] **Step 4: Verify the long script gate**

Run the user's original script through the planner. Expected: `needs_script_confirmation` if over 90 seconds, exact original text in the error status, and no output directory.

- [ ] **Step 5: Commit only distributable example files if appropriate**

Runtime jobs and real assets remain outside Git. Commit no real voice/avatar IDs or media.

---

### Task 8: Full verification and install the finished Skill

**Files:**
- Source: `D:\数字人智能体\rachel-digital-human-production\.worktrees\digital-human-framework`
- Install target: `C:\Users\78575\.codex\skills\rachel-digital-human-production`

- [ ] **Step 1: Run the full suite in both encoding modes**

```powershell
Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
python -m unittest discover -s tests -v
$env:PYTHONUTF8='1'
python -X utf8 -m unittest discover -s tests -v
```

Expected: zero failures, errors, or reader-thread exceptions.

- [ ] **Step 2: Validate structure and scan safety**

```powershell
python -X utf8 C:\Users\78575\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
rg -n "MiniMax|MINIMAX_API_KEY|HEYGEN_API_KEY|api\.minimaxi\.com|api\.heygen\.com|Authorization:" SKILL.md README.md agents references scripts
git diff --check
git status --short
```

Expected: no production-route or secret matches; only intended runtime-external dirty files, if any.

- [ ] **Step 3: Verify the approval gate and App-only plan**

Run direct probes proving:

- a bare approval boolean cannot enter `post_production`;
- a preview cannot enter `post_production`;
- a matching full raw can enter only with bound evidence;
- action plans contain only HeyGen App tool names and no endpoint/key;
- HyperFrames appears only after `post_production` in the Skill.

- [ ] **Step 4: Back up the installed Skill safely**

Resolve the exact install directory, copy it to a timestamped sibling backup, and verify neither path is a symlink or workspace root. Do not delete the old copy.

- [ ] **Step 5: Install distributable content only**

Copy `SKILL.md`, `agents`, `references`, and `scripts`. Keep the repository `README.md` as source-project documentation, but do not install it as Skill runtime content. Exclude `.git`, `.worktrees`, `tests`, `docs/superpowers`, media, runtime assets, jobs, logs, credentials, and caches.

- [ ] **Step 6: Validate the installed copy**

```powershell
python -X utf8 C:\Users\78575\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\78575\.codex\skills\rachel-digital-human-production
rg -n "MiniMax|MINIMAX_API_KEY|HEYGEN_API_KEY|api\.heygen\.com" C:\Users\78575\.codex\skills\rachel-digital-human-production
```

Expected: installed Skill valid and HeyGen App-only.

- [ ] **Step 7: Commit final verification fixes**

If verification required changes, stage only those files, run `git diff --cached --check`, and commit `test: verify HeyGen plan-credit workflow`.

Do not clone a voice, create speech, create an avatar/look, or render a video during Tasks 1-8. Those are separate plan-credit integration actions requiring an explicit user confirmation after the installed Skill is verified.
