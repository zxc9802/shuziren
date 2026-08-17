# Boss View Modes

Use one view mode for each newly generated boss look:

| User-facing option | Plan value | Pose and gaze anchor |
|---|---|---|
| 正面 | `front` | Torso and head face front; gaze meets the lens. |
| 左侧 45° | `three_quarter_left_45` | Torso and head turn together about 45° toward frame left; gaze stays on a natural off-camera point in that direction. |
| 右侧 45° | `three_quarter_right_45` | Torso and head turn together about 45° toward frame right; gaze stays on a natural off-camera point in that direction. |

Ask exactly: **“这次生成的老板形象采用正面，还是45°侧面（左转或右转）？”** Record the answer only for the current job. If the user writes “45%” while describing an angle, confirm or interpret it as about 45 degrees only when that intent is clear.

## 45° side-mode contract

- Treat “侧面” as a three-quarter view, not a 90° profile.
- Rotate the torso, shoulder line, neck, and head together. Do not leave the torso frontal and twist only the neck or eyes.
- Keep the existing seated close upper-body scale. “整个身体和头部转 45°” describes orientation, not head-to-toe full-body framing. If the user explicitly requests head-to-toe framing, stop and clarify because it conflicts with the current close, Avatar IV-safe brand baseline.
- Keep both eyes anatomically plausible for the angle. Avoid excessive sclera, crossed gaze, side-eye toward the lens, or eyes that point in different directions.
- In motion, keep the camera fixed and treat the selected 45° pose plus its off-camera gaze point as the neutral anchor. Blinks, micro-expressions, and small phrase-led head motion return to that anchor; never alternate to direct eye contact.
- Reject a candidate when torso, head, and gaze do not share the approved direction, the turn reads as 90° profile, the neck is overtwisted, or the framing becomes full-body or distant.

Side mode requires an approved generated or existing side-view look. Do not claim that the frontal `original_image1` satisfies it.

Pass the recorded plan value through the task overrides as `view_mode`; `scripts/plan_job.py --dry-run` must preserve it in `task.json`, `visual-plan.json`, `performance-plan.json`, and the internal HeyGen pre-submit checks.
