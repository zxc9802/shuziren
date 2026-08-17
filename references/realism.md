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

## Motion irregularity

Keep camera and framing fixed. Then make the performance imperfect on purpose:

- Blink intervals must be uneven. Never use a metronome blink.
- Allow occasional small saccades that return to the gaze anchor. For `front`, the anchor is the lens. For either 45-degree side mode, the anchor is the same-direction off-camera conversation point; never twist the eyes back to the lens.
- On emphasis, let the brows lead and the head lag by about half a beat.
- Insert a swallow or breath-style micro-pause at a few semantic boundaries, not inside a complete Mandarin phrase.
- Allow tiny torso weight shifts. Keep the selected front or 45-degree pose-and-gaze as the home position.
- Complete at most one prepare-stroke-retract-cooldown hand cycle, then return hands to neutral before another gesture.
- Ban any motion that repeats on a fixed period, continuous gesturing, mechanical face/head/hand synchrony, fused hands, or invented limbs.

## Realism QA gate

Run this gate on every completed preview and every completed full raw before delivery. A failure makes the artifact ineligible. Do not treat a realism failure as something ChatCut can fix.

- Skin does not look retouched, poreless, plastic, or waxy.
- Glasses reflections and refraction track head motion; lenses never read as empty frames.
- Resting hands do not freeze into a wax-figure pose; micro-motion remains present when no gesture is active.
- Background bokeh stays stable and does not "breathe".
- Blink timing is irregular; no looping sway or metronome head bob.
- For side-mode jobs, gaze stays on the same-direction off-camera point and never snaps back to the lens.

If the gate fails, report the exact failed check and stop. Retry only the failed render stage after a corrected motion prompt or a newly adopted look; never submit a duplicate paid render merely to re-check the same file.
