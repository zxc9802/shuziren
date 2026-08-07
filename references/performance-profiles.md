# Performance Profiles

## `business-human-1`

`business-human-1` captures reusable behavior observed in the user-approved Douyin business talking-head reference. It is a semantic performance language, not a copied timeline, outfit, background, or fixed prompt.

### Base posture and camera

- Use a locked camera and stable framing. Do not zoom, pan, tilt, reframe, or add camera shake.
- Keep the torso stable with only breathing, restrained weight shifts, a brief semantic lean, and a complete return to neutral.
- Use one anchor hand and one lead hand when the source supports them. Keep the anchor visually stable; let the lead hand carry at most one small semantic action at a time.
- Start from a neutral ready pose with clear mouth, jaw, eyes, eyewear, wrists, and available fingers. Preserve space around the head, shoulders, and lead hand.

### Channel timing

Drive gaze/face, head, hands, and body from semantic beats and the measured HeyGen speech timeline. Stagger their starts and peaks so they do not activate or settle together. Prefer face or gaze first, then a small head response, then an optional hand stroke; body motion remains quiet.

Blink irregularly and return gaze to camera after short natural offsets. Use small head adjustments and occasional phrase-ending nods. Never create periodic nodding, pendulum head sway, continuous waving, continuous shoulder motion, or motion merely to fill time. When no semantic trigger exists, hold a living but quiet idle.

### Semantic candidates

Candidates are optional. Select with context, recent-action history, cooldown, source pose, topology, and Avatar IV capability.

| Role | Face and gaze | Head | Optional lead-hand/body candidate |
|---|---|---|---|
| Hook | direct gaze, slight brighten | micro-forward settle | small opening beat |
| Question | light eyebrow lift | small tilt | restrained open palm |
| Explanation | attentive neutral | micro-nod | palm-up or small arc |
| Warning | slight brow narrow | brief stillness | restrained vertical palm or index cue |
| Contrast | gaze holds the turn | small recenter | short lateral separation |
| Steps | clear focus | phrase beat | small counting beat, not finger-by-finger automation |
| Conclusion / CTA | calm certainty | one settled nod | compact CTA gesture, then settle |

Do not repeat the same main gesture in adjacent beats. A candidate may be omitted when the source image, recent motion, speech density, or provider capability makes stillness more natural.

### Complete action cycle

Every main gesture follows:

```text
prepare -> stroke -> optional hold -> retract -> cooldown
```

Release the lead hand from its anchor, perform one readable stroke, hold only if semantic emphasis benefits, fully return to the resting anchor, then leave a cooldown before another trigger. Do not cut from a stroke into the next gesture or leave the hand suspended.

Use actual audio intervals to scale these relative phases. Faster or shorter speech compresses preparation/hold/cooldown; slower or weightier speech gives the same phases more room. Do not encode fixed seconds, word-index choreography, exact coordinates, or promises of frame-accurate gesture timing.

### Source-image topology downgrade

| `hand_topology` | Allowed behavior |
|---|---|
| `separated` | Use one restrained lead-hand semantic gesture; keep the other hand anchored and both hands anatomically separate. |
| `one_visible` | Use only the visible hand as lead; anchor or suppress the obscured side and never imply an extra limb. |
| `overlapping` | Keep hand motion minimal and near the resting anchor; move expression to gaze, face, head, stillness, and breathing. Avoid finger counting, crossing, or separation attempts. |
| `not_visible` | Use no hand gestures. A close-up must not invent, extend, or animate arms/hands outside the source frame. Use face, head, and subtle body cues only. |

The visual plan and Frame Check determine topology before motion-prompt compression. Automatic inference is the default; safe presentation overrides may refine wardrobe, scene, framing, or platform needs but cannot weaken topology limits. If topology confidence is low, choose the safer downgrade. HeyGen receives a concise capability-aware overall prompt; automatic QA evaluates naturalness, anatomy, return-to-rest, and nonperiodic motion rather than exact reproduction of the plan.
