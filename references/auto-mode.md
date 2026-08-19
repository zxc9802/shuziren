# Auto Mode

Use this reference only after the current job records `operating_mode=auto`.
Interactive jobs must keep asking the per-job questions and must not inherit
these defaults.

## When to use auto

Record `auto` when the user asks for 全自动, 自动模式, or 不用确认, or when
they supply a script and say that the job should finish without mid-flow
approvals. Do not infer auto from silence, an earlier job, or spend consent
alone.

Interactive remains the default when the user does not request auto.

## Locked defaults

These values are the auto-mode defaults. Apply them without asking. A same-turn
explicit override in the auto request may change only the named field; do not
reopen the other gates.

| Gate | Default | Why |
| --- | --- | --- |
| Voice provider | `minimax` (`huangxu1`) | Already the recommended clone; exact audio; HeyGen must not re-synthesize. |
| Company materials | `none` | Auto cannot safely pick B-roll; talking-head copy stays material-free. |
| Script | Incoming copy is the approved script | The user already supplied the words to speak. |
| New boss look | no | Skip four-candidate review; keep identity stable. |
| Identity source | `original_image1` | Front-view master; default job look. |
| View mode | `front` | Matches `original_image1`; do not claim a side view. |
| Preview | disabled | Avoid a second paid render and a preview-approval wait. |
| Raw approval | auto-bind after QA pass | Reviewer is `auto-mode`; evidence is the QA-passed raw. |
| Post-production | ChatCut, no-material route | Deliver a packaged talking-head with script-grounded MG, not only the raw. |
| A-roll gate | Automatic QA, reviewer `auto-mode` | Preserve the gate without interrupting a full-auto job for human approval. |

Do not generate a new look, do not ask MiniMax vs HeyGen vs IndexTTS-2, do not ask about
company materials, and do not ask about a 15-second preview.

## Auto job order

1. Confirm the connected HeyGen account with `get_current_user` before spend.
   Invoking auto with a script is the job's rights and credit-spend consent.
   Stop if the account, clone, identity, or credit source cannot be verified.
2. Record `operating_mode=auto`, `voice_provider=minimax`,
   `material_route=none`, `image_generation_choice=use_original`,
   `selected_image_source=original_image1`, `view_mode=front`, and
   `preview_choice=disabled`. Read `references/voice-routing.md` for the
   MiniMax route unless the same-turn auto request named IndexTTS-2 or HeyGen. Do not read `references/material-routing.md` unless the user
   overrode the material default to `company`.
3. Treat the supplied Mandarin as the approved script. If it contains awkward
   phrasing or unsafe TTS breaks, rewrite it as natural spoken Mandarin, keep
   the meaning, and continue without waiting. If estimated duration is below
   15 seconds, stop; do not invent extra sentences.
4. Plan with `scripts/plan_job.py --auto --dry-run`, then apply
   `scripts/update_job_state.py apply-auto-defaults` so the job reaches
   `preview_choice_recorded` on `original_image1` with preview disabled.
5. Run `python3 scripts/verify_performance_reference.py --json`, require the
   planned `business-human-123-v1` performance-only binding, then resolve the
   existing `image1` look that matches `original_image1`. Do not create a new
   photo-avatar look for the default original image when a ready Avatar IV look
   already exists.
6. Read `references/performance-system.md`. Write `voice-plan.json` from the exact approved text, synthesize MiniMax `huangxu1` by segment, preserve measured final-audio boundaries, and run `scripts/build_performance_beat_map.py`. Require the beat map to bind the exact final-audio SHA-256, then upload that MP3 and submit one structured Avatar IV portrait `9:16` `720P` full raw. Skip preview.
7. Persist and poll the same video ID. After download, run `scripts/compare_performance_reference.py` and full-file QA including the realism gate. `reject_and_rerender`, missing evidence, or any other QA failure is a hard stop; do not auto-approve or enter ChatCut. Diagnostic clearance alone does not replace the rest of auto QA.
8. On QA pass, record bound raw approval with reviewer `auto-mode` via
   `approve-raw-auto`, then enter ChatCut on the no-material route. Read
   `references/chatcut-editing.md` and `references/chatcut-mg.md`. Finish A-roll
   through ChatCut Script, write `chatcut-a-roll-report.json`, and run every
   locked A-roll auto-QA check. Continue only when that report records
   `review_status: approved` with reviewer `auto-mode`; otherwise stop before
   captions, B-roll, MG, sound effects, or music. On pass, apply the remaining
   package and deliver the final packaged video.

## Still-hard stops

Auto skips confirmation, not verification. Stop with the exact blocker when:

- HeyGen authentication, account mismatch, or insufficient credits;
- MiniMax `huangxu1` cannot be verified or synthesized;
- `business-human-123-v1` is missing, changed, or not bound as performance-only;
- the primitive library is changed/unbound, a beat has an illegal primitive chain, or a MiniMax beat map does not bind the exact final-audio SHA-256;
- the rendered comparison evidence is missing or recommends `reject_and_rerender`;
- ChatCut A-roll auto-QA fails, lacks `chatcut-a-roll-report.json`, or is not bound to reviewer `auto-mode`;
- `original_image1` or a ready Avatar IV look cannot be bound;
- the script is empty or shorter than 15 seconds;
- lossless `voice-plan.json` fails;
- plugin submission, upload, or polling is blocked;
- realism or full-file QA fails.

Never substitute a different voice, identity, provider, or script to bypass a
stop. Never linger in `awaiting_image_approval`, `awaiting_preview_approval`,
or `awaiting_raw_approval`; those states block the FIFO queue.

## Approval exception

Interactive jobs still forbid silence, `继续`, rights consent, or automatic QA
from substituting for image, preview, or raw approval.

Auto mode may bind raw approval only when all of the following are true:

- `assets.job_route.operating_mode` is `auto`;
- the full raw exists, `qa_passed` is true, and the HeyGen video ID matches;
- reviewer is exactly `auto-mode`.

`auto-mode` is not a valid reviewer for image or preview approval. Auto mode
does not generate a new look and does not render a preview, so those gates
never open.
