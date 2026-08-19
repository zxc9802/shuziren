# Fixed Brand Defaults

Apply these defaults to future jobs unless the user explicitly overrides them for that job.

## Enterprise AI IP

- Position the speaker as the company's practical enterprise-AI implementation IP: professional, credible, business-focused, and oriented toward turning AI into repeatable daily workflows.
- Prefer concrete job scenarios, implementation steps, measurable outcomes, human accountability, and gradual rollout over abstract technology claims.
- Keep the speaker recognizable as the same boss identity represented by `image1`; do not change identity traits.

## General distribution profile

- Produce a platform-neutral vertical master suitable for common short-video channels.
- Use portrait `9:16`, keep important face/body content inside a conservative center safe area, and avoid platform-specific watermarks, handles, stickers, or calls to action unless requested.
- Keep the raw-generation contract unchanged: Avatar IV, `720P`, fixed camera, captions/music/B-roll/MG/transitions off. Add captions, script-grounded MG, branding, BGM, cover, or platform-specific packaging only after the exact full raw is approved.
- Follow applicable AI-generated-content disclosure requirements when publishing. “General distribution” does not waive platform policy checks.

## Generated job-look defaults

Apply these defaults whenever the user chooses to generate a new boss image, unless the user explicitly overrides them for that job:

- Use assets/original_image1.png as the identity master and as the baseline for close seated camera distance, eye level, subject-to-frame scale, head-and-shoulder size, torso crop, foreground forearms, and complete hand visibility. Keep the person at the same scale or closer and never convert the look to a standing or head-to-toe full-body composition. Do not force an exact reproduction of the source pose.
- Change wardrobe, background, and at least one natural pose detail by default. Compare with the most recent generated or previously adopted look only to avoid repeating the same exact pose across jobs; do not use it as a replacement identity source. Record the most recent look's **gesture signature** and exclude that signature from the next job's candidate round. Within one four-candidate round, keep wardrobe, background, view mode, framing, and requested expression consistent, but use **four distinct two-hand pose families** rather than four phases of one gesture. At most one candidate may use one open palm while the other hand lies flat. Include safe alternatives such as **both hands resting separately**, **both hands lifted asymmetrically**, and **one hand near the torso** while the other remains lower and farther away. Keep every variation seated, anatomically safe, and suitable for Avatar IV. Use direct-to-camera gaze only for `front`; for a selected 45° side mode, follow `references/view-modes.md` and keep torso, head, and off-camera gaze on the same directional anchor. Unless the user explicitly requests another expression, use the ordinary neutral-expression contract in `SKILL.md`; pose variation must not introduce a smile, micro-smile, or stern promotional expression.
- Keep both elbows, forearms, wrists, hands, and every visible finger completely inside the frame with comfortable margins. Keep the hands anatomically correct and suitable for restrained animation.
- Choose relaxed seasonal clothing from the current local date and location. Prefer T-shirts, polos, overshirts, light knits, cardigans, or casual jackets appropriate to the season. Avoid suits, ties, formal blazers, and overly formal styling unless the user explicitly requests them.
- Choose a script-appropriate setting from a rotating family of premium business locations suitable for a company boss: an executive office, a Class-A office tower lounge, a high-rise meeting room, a polished corporate reception area, an upscale business cafe, a premium business-hotel cafe or executive lounge, or another high-quality business space. This is a location category, not one fixed room; vary the layout, architecture, dominant materials, window view, and color mood across jobs while keeping the environment credible and professionally restrained.
- Require a photorealistic, physically buildable location with correct perspective, ordinary high-quality architectural details, believable materials, natural reflections, and plausible mixed lighting. Unless the user explicitly requests one for the current job, reject industrial workshops, factory floors, warehouses, storage rooms, ordinary employee cubicle areas, residential rooms, street scenes, ordinary casual cafes that lack an upscale business atmosphere, ostentatious mansion-like interiors, CGI sets, futuristic studios, artificial geometric feature walls, plastic showrooms, surreal architecture, and fake depth-of-field.
- Preserve `image1` identity invariants and keep portrait `9:16`, view-mode-appropriate gaze, fixed-camera-friendly framing, conservative safe margins, and topology-safe hands.
- Reject a candidate before display if the person is smaller or farther from camera than original_image1, the seated crop becomes unsafe, it repeats the same exact pose, it uses an extreme or animation-unsafe pose, it is full-body, it crops either hand/wrist/elbow, it uses overly formal clothing without an override, it repeats the most recent background, its background falls outside the premium-business category without an explicit override, the background looks synthetic or ostentatious, or it drifts from the identity master.

## Mandarin script and TTS phrasing defaults

- Draft or rewrite scripts in natural spoken Mandarin before planning. Prefer complete, grammatically natural subject-predicate-object phrasing over literal or compressed wording.
- Put punctuation only where a human speaker should breathe. Use full stops for complete semantic beats and commas only for genuine short pauses. Do not insert punctuation or line breaks inside a subject-predicate unit, verb-object/complement unit, modifier-head unit, fixed phrase, number-plus-unit, proper noun, or the two sides of a required collocation.
- Run a read-aloud pass before asking for script approval. Reject every “用进……工作” construction, including “不会用进日常工作” and “把 AI 用进每天的工作”. Also reject a pause such as “员工不知道，怎么……” or “这，才是……”. Prefer “员工不知道怎样把 AI 用到日常工作中” and “这才是……”.
- Do not use zero-width characters, word joiners, or hidden SSML-like markup to repair an awkward sentence. Rewrite the visible Mandarin naturally, show the complete script, and wait for explicit approval.
- After the user approves the rewritten script, preserve that approved text byte-for-byte through planning and submission.

## Fixed identity source

- Resolve both `image1` and 原始图片1 from `assets/original_image1.png` for local identity reference and preflight.
- Expected SHA-256: `1dc7351e199948c7acdb96589073d20effa51fdf155a9b24da22b939af396966`.
- Treat the image as a private authorized local asset. Never publish or package it with a publicly shared copy of this skill.
- Use it as the identity master and the default job look only. A generated job look may change wardrobe, pose, background, lighting, framing, and props, but must preserve face shape, features, apparent age, skin tone, short black hairstyle, black rectangular eyewear, body type, and recognizability.

The stable MiniMax narration default is `huangxu1`. The IndexTTS-2 option uses the authorized speaker-reference URL in `.env` as `indextts_voice1`. Every synthesis also requires a script-specific `voice-plan.json` whose segments preserve the approved text losslessly and vary emotion and emotion intensity by semantic beat. These defaults do not supply a HeyGen `voice1` ID or `image1` avatar-group ID. Resolve those stable private HeyGen account records at runtime, and stop if they cannot be verified.
