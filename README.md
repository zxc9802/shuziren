# 数字人skill

用于批量生产经授权的 15-90 秒中文数字人口播视频。长期保持同一个老板身份 `image1` 和克隆声音 `voice1`，每个任务可以使用原始图片1，也可以生成一张新的服饰、姿势、背景、灯光和构图不同的老板形象。

## 核心流程

每个任务按以下顺序执行：

1. 校验授权、固定资产、文案和 15-90 秒时长。
2. 询问是否调用内置生图模型生成新的老板形象。
3. 不生成时使用原始图片1；生成时只生成一张候选图，并等待用户明确回复“采用”。
4. 询问是否需要 15 秒低成本预览。
5. 自动控制已登录的 HeyGen 网页，绑定已采用形象、`voice1`、原文、Avatar IV、9:16、720P 和完整动作提示，使用网页套餐额度点击一次生成。
6. 只有稳定 video ID、已绑定形象、真实视频资源和非零进度等页面证据成立时，才报告正在生成。
7. 预览、完整原片和 HyperFrames 包装分别确认；只有完整原片明确通过后才进入后期。

批量任务使用严格 FIFO 队列。队首等待图片、预览或原片确认时，后续任务全部停止，不并发消耗额度。

## 本地规划

```powershell
python scripts/plan_job.py `
  --script inputs/script.md `
  --registry inputs/assets.json `
  --out work/jobs/job-001 `
  --dry-run
```

规划会原子写入七个 JSON 文件；其中 `heygen-app-plan.json` 是兼容文件名，内部 transport 为 `heygen-web-plan-credits`。本地规划、状态更新和队列检查不会联网，也不会消耗 HeyGen 额度。

使用 `scripts/update_job_state.py --help` 查看 v3 状态事件，使用 `scripts/queue_jobs.py --help` 管理串行队列。

## 参考

- [Skill contract](./SKILL.md)
- [Framework](./references/framework.md)
- [Browser submission](./references/browser-submission.md)
- [Checklists](./references/checklists.md)
- [Performance profiles](./references/performance-profiles.md)

## License

MIT. See [LICENSE](./LICENSE).
