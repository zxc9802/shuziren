# 数字人skill

用于批量生产经授权的 15 秒及以上中文数字人口播视频。长期保持同一个老板身份 `image1` 和克隆声音，每个任务可以使用原始图片1，也可以生成一张新的服饰、姿势、背景、灯光和构图不同的老板形象。正面生图使用 `original_image1`；左转或右转的 45° 侧面生图使用 `assets/side-image1.jpg` 里的同一人物作为第一身份参考。

交互模式会逐项确认配音、素材、形象、预览和原片。全自动模式在用户明确要求「全自动」后，用锁定默认值把传入文案做到包装成片：MiniMax `huangxu1`、不插公司素材、原始正面形象、不做 15 秒预览，QA 通过后自动进入 ChatCut。

公开仓库只包含 Skill 代码、说明和测试，不包含真实人像、声音样本、客户视频或表演参考视频。安装后请在本地按 `references/brand-defaults.md` 和 `references/performance-reference-123.json` 配置已获授权的私有素材；这些媒体类型默认由 `.gitignore` 排除。

## 核心流程

每个任务先记录 `interactive` 或 `auto`。

交互模式按以下顺序执行：

1. 校验授权、固定资产、文案和至少 15 秒时长。
2. 询问 MiniMax、HeyGen 还是 IndexTTS-2 配音，以及是否加入公司素材。
3. 询问是否生成新的老板形象。
4. 不生成时使用原始图片1。生成前询问这次用 OpenLux `gpt-image-2-c` 还是 Codex 内置模型，再生成四张候选图并等待明确“采用第N张”。
5. 询问是否需要 15 秒低成本预览。
6. 用已连接的 HeyGen 插件绑定已采用形象、选定配音、原文、Avatar IV、9:16、720P 和完整动作提示，提交一次生成。
7. 只有稳定 video ID 和真实渲染证据成立时，才报告正在生成。
8. 预览、完整原片分别确认；只有完整原片明确通过后才进入 ChatCut 后期。本 skill 第 14 步仍执行完整剪辑流程，不要删掉。同一套包装也拆成了独立 skill `数字人剪辑`，只剪已有原片时用那个。后期在讲解节拍上按已批准文案加 MG 动画，不挡脸、不挡字幕。

全自动模式跳过第 2–5 步和第 8 步的确认，改走 `references/auto-mode.md` 的锁定默认值。账号、资产、时长和 QA 失败仍会停下来。

批量任务使用严格 FIFO 队列。队首等待图片、预览或原片确认时，后续任务全部停止，不并发消耗额度。

## 本地规划

```powershell
python scripts/plan_job.py `
  --script inputs/script.md `
  --registry inputs/assets.json `
  --out work/jobs/job-001 `
  --dry-run
```

全自动规划加上 `--auto`，会写入锁定默认值，并把 `state.json` 推到 `preview_choice_recorded`。

规划会原子写入七个 JSON 文件；其中 `heygen-app-plan.json` 是兼容文件名，内部 transport 为 `heygen-plugin-structured`。本地规划、状态更新和队列检查不会联网，也不会消耗 HeyGen 额度。

`performance-plan.json` 默认绑定本机私有的 `business-human-123-v1` 参考，只学习语音驱动的全身联动、活着的静止、眼神/眼睑变化和完整手势周期。运行 `python3 scripts/verify_performance_reference.py --json` 校验本地文件；该视频被 Git 忽略，永不上传到生成服务。

表演系统还会把每个语义段编译成版本化动作原语链。MiniMax 最终音频生成后，用 `scripts/build_performance_beat_map.py` 绑定真实分段边界和音频 SHA-256；HeyGen 原片下载后，用 `scripts/compare_performance_reference.py` 生成非像素式的全身联动对比报告、问题时间点和联系表。它不会比较人物身份，也不会把 `123` 的动作时间复制给 HeyGen。

使用 `scripts/update_job_state.py --help` 查看 v3 状态事件，使用 `scripts/queue_jobs.py --help` 管理串行队列。OpenLux 生图凭据放在 gitignore 的 `.env` 里，复制 `.env.example` 后填入 `OPENLUX_API_KEY`。

## 参考

- [Skill contract](./SKILL.md)
- [Auto mode](./references/auto-mode.md)
- [Framework](./references/framework.md)
- [Plugin submission](./references/plugin-submission.md)
- [Checklists](./references/checklists.md)
- [Performance profiles](./references/performance-profiles.md)
- [123 performance system](./references/performance-system.md)
- [Photographic realism](./references/realism.md)
- [Image-model routing](./references/image-model-routing.md)
- [ChatCut script-grounded MG](./references/chatcut-mg.md)
- Sibling standalone edit skill: `数字人剪辑`

## License

MIT. See [LICENSE](./LICENSE).
