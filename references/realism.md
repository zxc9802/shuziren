# Photographic realism

Use this file whenever a job generates a new boss look, writes a motion prompt, or QA-checks a preview or full raw. Identity, view mode, and pose rules in `SKILL.md` still win; this file only adds photographic and performance realism. Choose OpenLux or Codex per job using `references/image-model-routing.md` before any image call.

Match the documentary handheld-video-frame look of `original_image1` and `side_image1`. Do not match a studio advertisement, beauty portrait, or CG render.

## Image-prompt requirements

Apply all of the following to both `front` and 45-degree side generation.

### Skin

- Preserve visible pores, mild natural shine on forehead/nose/cheeks, slightly uneven skin tone, and small real-life imperfections.
- Keep apparent age; do not beautify, slim, sharpen the jaw, enlarge the eyes, or make the subject younger.
- Ban beauty retouching, skin smoothing, plastic or waxy skin, poreless makeup-filter skin, and over-sharpened "AI portrait" texture.

### Camera and capture

- Render as a natural video-frame capture: modest dynamic range, faint sensor noise, and shallow but believable depth of field.
- Keep the camera natural and stable. Ban HDR glow, cinematic color grading, film-grain stylization, and over-polished studio lighting.

### Eyewear

- Require real lens behavior: visible environmental reflections on the lenses, and a slight refraction offset of the cheek or jaw contour seen through the lens edge.
- Keep the approved eyewear shape. Lenses must never read as empty frames.

### Light

- Every light must have a plausible source such as window daylight or practical lamps.
- Ban sourceless even fill, floating rim light, and beauty-dish wraparound light that erases facial volume.

### Fabric and setting

- Clothing must show real weave, natural collar collapse, and seated-posture wrinkles. Ban smooth 3D-render cloth.
- Background bokeh must look optical, not painterly cream. Do not add extra people, text, watermarks, or distracting props.

## Side-view geometry

For `three_quarter_left_45` and `three_quarter_right_45`, use `side_image1` as the first and controlling person reference for identity and side-face geometry only. Do not inherit its navy polo, sofa, clasped hands, background, framing, or open-mouth expression unless the current job explicitly requests those elements.

Verify all of the following before displaying a side candidate:

- Head, neck, shoulders, and torso rotate together about 45 degrees toward the selected side.
- The nose points diagonally toward that side; the far cheek visibly narrows; both eyes remain visible. Reject a frontal result and reject a 90-degree profile.
- Far-eye perspective foreshortening is correct; the nose bridge partially occludes the far eye corner.
- Ear position and the ear-to-jawline junction look natural.
- The near glasses temple arm follows correct perspective.
- The hairline transition at the temple looks natural.

Because `side_image1` records only one real facing direction, when generating the mirrored side describe the subject's asymmetric details — hair part direction and any facial asymmetry — explicitly in the prompt. Never let the model silently mirror those details.

## Candidate inspection

A candidate is ineligible if it fails any of: identity, selected view mode, requested expression, complete separated hands, finger anatomy, framing, photographic realism, side-view geometry, or the assigned gesture signature.

Mark the rejected slot. Do not silently generate extra candidates in the same round to replace it.

## Motion-prompt authoring style

Write every motion block as a positive, present-tense description of a real person mid-conversation, not a list of prohibitions. A ban-dominated prompt reads as "hold still" and produces the frozen, waxy performance that users report as stiffness.

- Spend most of the prompt describing what the person is doing: breathing, blinking, weighing a phrase, letting a nod ripple through the shoulders, letting a gesture come to rest.
- Anchor described motion to the actual script's beats — the hook, the contrast, the conclusion — so movement reads as motivated by meaning rather than random fidgeting or imposed choreography.
- State the living idle floor explicitly in every motion prompt. Silence about idle behavior is what lets the model freeze between gestures.
- Compress all prohibitions into one short closing clause. Never let bans outnumber the life description, and never submit a motion prompt that only forbids.

## Living idle floor

Stillness must stay alive. Between gestures, during pauses, and across listening beats, all of the following continue for the whole take:

- Quiet breathing stays visible as a gentle chest-and-shoulder rise and fall.
- The head keeps a barely visible one-to-two-degree drift with small resettles; it is never bolted in place.
- Resting hands and fingers keep natural micro-relaxation — a fingertip eases, a knuckle softens — and never freeze into a wax pose.
- Eyes stay moist and attentive with irregular blinks; facial muscle tone keeps sub-visible shifts.

A freeze-frame idle is a stiffness defect, not restraint.

## Coupled, speech-led motion

- Head motion rides on the neck and shoulders: every head turn or nod carries a slight neck lean and shoulder response that the torso absorbs. Never rotate the head on a frozen body like a turret.
- Speech shows in the whole face: the jaw genuinely opens on open vowels, cheeks and nasolabial folds respond, and the throat moves on emphatic beats. Reject lip-only articulation on an otherwise static face.
- Head and brow micro-accents track the prosody of the actual narration — a slight nod or brow lift lands on stressed syllables, a soft settle lands at clause ends — so motion reads as caused by the audio rather than layered on top of it.

## Motion irregularity

Keep camera and framing fixed. Then make the performance imperfect on purpose:

- Blink intervals must be uneven. Never use a metronome blink.
- Allow occasional small saccades that return to the gaze anchor. For `front`, the anchor is the lens. For either 45-degree side mode, the anchor is the same-direction off-camera conversation point; never twist the eyes back to the lens.
- On emphasis, let the brows lead and the head lag by about half a beat.
- Insert a swallow or breath-style micro-pause at a few semantic boundaries, not inside a complete Mandarin phrase.
- Allow tiny torso weight shifts. Keep the selected front or 45-degree pose-and-gaze as the home position.
- Complete at most one prepare-stroke-retract-cooldown hand cycle, then return hands to neutral before another gesture.
- Ban any motion that repeats on a fixed period, continuous gesturing, mechanical face/head/hand synchrony, fused hands, or invented limbs.

## Stability limits

Avatar IV warps when asked to move too much, too fast, or in several channels at once. Instability is a motion-budget problem, not bad luck:

- Keep gestures compact, unhurried, and forearm-led near the torso. Large or fast full-arm strokes cause hand melt, finger smearing, and sleeve warping at stroke peaks.
- Stagger the channels: a hand stroke, a head accent, and a torso shift must not peak together. One primary motion at a time, with face and gaze leading.
- Identity stays locked while moving: facial geometry, eyewear, hairline, and ears must not warp, swim, or flicker during turns and emphasis.
- Clothing pattern, background structure, and framing must not crawl, breathe, or jitter between frames.
- When the script is long or gesture-heavy, prefer adopting a look whose hands rest on a support; hands suspended mid-air in the source image carry a higher stroke-peak warp risk in animation.

## Realism QA gate

Run this gate on every completed preview and every completed full raw before delivery. A failure makes the artifact ineligible. Do not treat a realism failure as something ChatCut can fix.

- Compare channel relationships against the verified `business-human-123-v1` performance reference, not its identity or styling. Reject a hands-led take whose face, head, neck, shoulders, and torso remain disconnected; use the manifest ratios only as diagnostic evidence, never as fixed motion targets.
- Run `scripts/compare_performance_reference.py` on the downloaded artifact and inspect its rendered contact sheet at the reported worst timestamps. The comparison deliberately excludes identity and pixel similarity. `reject_and_rerender` fails this gate; `eligible_for_human_review` still requires the visual checks below.
- Inspect the total audio track for repetitive dead-silence restarts at segment boundaries. Natural semantic pauses are allowed, but a recurring stop-start cadence that repeatedly freezes and relaunches the avatar fails performance realism.
- Skin does not look retouched, poreless, plastic, or waxy.
- Glasses reflections and refraction track head motion; lenses never read as empty frames.
- Resting hands do not freeze into a wax-figure pose; micro-motion remains present when no gesture is active.
- Breathing stays visible at the chest or shoulders across the whole file; the person never reads as a statue with a moving mouth.
- Head motion carries a neck-and-shoulder response absorbed by the torso; reject turret-head rotation on a frozen body.
- Speech energy reaches the jaw, cheeks, and brows, with micro-accents landing on stressed syllables; reject lip-only articulation on a static face.
- Facial geometry, eyewear, hairline, and ears stay stable through head turns and emphasis — no warping, swimming, or flicker.
- Hands keep their shape through every gesture; no finger melt, fusion, or smearing at stroke peaks.
- The frame is steady: no frame jitter and no crawling in clothing pattern or background structure.
- Background bokeh stays stable and does not "breathe".
- Blink timing is irregular; no looping sway or metronome head bob.
- For side-mode jobs, gaze stays on the same-direction off-camera point and never snaps back to the lens.

If the gate fails, report the exact failed check and stop. Retry only the failed render stage after a corrected motion prompt or a newly adopted look; never submit a duplicate paid render merely to re-check the same file.
