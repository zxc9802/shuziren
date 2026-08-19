# 123 Performance System

Use this reference after `performance-plan.json` exists, again after the exact
final narration exists, and again when a preview or full raw has downloaded.

## 1. Legal performance primitives

`references/performance-primitives.json` is the only legal primitive vocabulary
for `business-human-1`. `performance-plan.json` binds its exact SHA-256 and gives
every semantic beat a `primitive_chain` that begins with `living_idle` and ends
with `phrase_settle`. When hands are disabled, the chain must omit
`hand_stroke`.

The chain is semantic and relative. It may tell the provider that the face
leads, the head follows, the neck and shoulders absorb, the torso
counterweights, an optional hand stroke completes, and the phrase settles. It
must not claim frame-accurate provider control or copy the 123 video's exact
gesture timestamps.

## 2. Exact-audio performance beat map

On the MiniMax or IndexTTS-2 route, synthesize every `voice-plan.json` segment separately,
preserve the exact segment text and file, concatenate in approved order, and
measure the real boundaries in the concatenated final audio. Write
`final-audio-segments.json`:

```json
{
  "source": "minimax_concatenated_segment_boundaries",
  "segments": [
    {
      "id": "beat-001",
      "text": "Exact approved text.",
      "start_seconds": 0.0,
      "end_seconds": 2.84
    }
  ]
}
```

Then run:

```bash
python3 scripts/build_performance_beat_map.py \
  --voice-plan <job>/voice-plan.json \
  --performance-plan <job>/performance-plan.json \
  --timings <job>/final-audio-segments.json \
  --audio <job>/exact-final-minimax.mp3 \
  --out <job>/performance-beat-map.json
# IndexTTS-2 uses exact-final-indextts.wav as --audio.
```

The command rejects changed text, changed beat IDs, overlaps, gaps at the start
or end, duration mismatch, an invalid audio file, or an existing output. The
result binds the exact final-audio SHA-256 and records entry, readable-hold, and
settle checkpoints for planning and rendered QA only.

On the HeyGen-voice route, no exact final audio exists before spend. Do not
invent timestamps. After the raw downloads, derive segment boundaries from its
local transcript and build the map for rendered QA; the map is not a provider
instruction.

## 3. Rendered performance comparison

Run this on every downloaded preview and full raw before approval:

```bash
python3 scripts/compare_performance_reference.py <candidate.mp4> \
  --out <job>/qc/performance-<preview-or-full-raw>
```

The local analyzer verifies the frozen 123 reference, uses macOS Vision for
face geometry when available, samples regional optical flow, and compares these
relationships:

- upper-face response relative to mouth motion;
- head, shoulder, and torso response relative to hand motion;
- hand-active spans with inadequate whole-person support;
- mouth-active spans where non-mouth living idle collapses;
- fixed-period motion risk.

It writes:

- `performance-qc.json`;
- `realism-review.md`;
- `comparison-contact-sheet.jpg`.

The comparison is not identity recognition, SSIM, PSNR, pixel matching, or a
request to reproduce the same gesture. Different framing, wardrobe, background,
aspect ratio, and person are deliberately ignored. Contact-sheet pairs use
normalized progress only and do not claim matching words or actions.

`reject_and_rerender` is a realism-gate failure. Fix the earliest failed
performance contract and obtain explicit authority before another paid render.
`eligible_for_human_review` means only that no diagnostic threshold failed; it
does not approve eyes, mouth shape, anatomy, identity stability, or overall
naturalness by itself. Auto mode may combine this evidence with its complete
existing QA gate, but this report alone never grants approval.

## Privacy and dependencies

Both videos stay local. Never upload the 123 reference as provider input or
include it in a public deliverable. Performance comparison requires local
`ffmpeg`, `ffprobe`, Python `cv2`, Python `numpy`, and on macOS uses the bundled
Vision helper without downloading a face model. A missing dependency or failed
face localization is a hard diagnostic blocker, not a passing result.
