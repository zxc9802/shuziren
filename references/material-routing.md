# Company Material Routing

## Core rule

对素材路线执行“先盘点素材，再写文案”。文案中必须出现与当前真实素材能力直接相关的素材相关文案；不得先写泛文案再硬塞素材。

## Route decision

Ask exactly: **“这个任务是否需要加入公司素材？”**

- On explicit no, use the normal talking-head route. Do not add material-dependent claims or company B-roll.
- On explicit yes, inspect the available real company assets before writing. Record the choice only for the current job.

## Grounding the script

Build a small asset inventory with asset reference, visible function, safe claim, usable range, and privacy notes. Prefer these verified categories when present:

- 多手机账号矩阵：内容自动发布、账号矩阵运营或真实终端运行。
- 销售或客户分析智能体：客户沟通、对话分析或需求整理。
- 内容创作工作台：脚本、图片、视频或创意生产。
- 商品视觉智能体：商品图、视觉方案或营销素材生产。

Write the narration around selected assets. A selected asset must have at least one sentence that truthfully explains what viewers are seeing, such as “我们把内容生产和账号发布拆成可以持续运行的智能体流程”. Do not claim a customer, result, metric, delivery, or feature that the material does not prove.

- 每条素材路线视频只选择与已批准文案最相关的 1–2 类真实公司素材；不得为了展示素材库而串联全部素材。
- 素材不相关或不能准确证明当前表达时，保留数字人口播画面，不用无关素材填满时间线。

## Supporting generated still

每条素材路线视频只生成 1–2 个 AI 补充素材。默认从一张专属补充图片开始，只有两个不同内容缺口都需要可视化时才生成第 2 个。

After script approval, generate the approved small set of script-specific supporting assets only when a real-material gap benefits from visualization. Use a realistic office-shot style such as a materials library, document library, test record, workflow, or project folder. Prefer readable business folder and document names. Avoid fake report covers, customer identities, confidential values, fabricated metrics, and unimplemented features.

Treat the still as illustrative, not proof. Add an appropriate “场景示意” disclosure when public viewers could mistake it for a real business record.

## Material plan

Create `material-plan.json` only after the script is approved. Each entry records:

- exact narration sentence;
- transcript start and end;
- real video, real frame, or generated still;
- source path or ChatCut asset ID;
- source in/out range and screen duration;
- full clip, excerpt, or key-frame use;
- selection reason;
- crop, motion, transition, and flower-text direction;
- provenance and disclosure requirement.

Default for an approximately 90-second material-route video: one or two selected real company-asset categories plus one generated supporting asset. A second generated asset is allowed only for a separate visual gap. Do not exceed two real categories or two generated assets merely to add visual variety.

## ChatCut placement

Use word-level timestamps from the final post-speed transcript, only after the A-roll approval/auto-QA gate and captions. Insert each asset at the start of its grounded sentence and return to the approved talking head when that explanation ends. Real clips normally use the strongest 2-6 seconds. Static stills normally use 3-5 seconds with restrained push or pan motion. Preserve the A-roll sound and mute or omit B-roll source audio unless the user explicitly requests it.

Do not cover essential subtitles or product UI. Preserve the approved raw, identity, lip sync, and voice. Place approved company material before writing `mg-plan.json`, so MG fills only uncovered explanation beats. Continue the standard ChatCut package with restrained business-tech flower text, speech-led sound effects, original no-vocal BGM, voice ducking, and final `smooth_audio`. Read `references/chatcut-editing.md` and `references/chatcut-mg.md`. Do not overlap an MG with a company B-roll or supporting still on the same span.
