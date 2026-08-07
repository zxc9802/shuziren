# HeyGen 套餐额度数字人生产 Skill 设计

日期：2026-08-07
状态：已获用户口头确认，待书面复核
取代：原 MiniMax＋HeyGen 生产路线

## 1. 目标

把 `rachel-digital-human-production` 完成为一套可长期复用的数字人生产 Skill：声音克隆、语音合成、数字人身份和 Avatar IV 原片全部使用 HeyGen App 当前登录账户的套餐能力，不使用 MiniMax，不要求 API Key，不直接调用 HeyGen HTTP API，也不使用按量 API 计费路线。

完整 Skill 继续负责：

- `声音1`、`图片1` 等授权资产的注册和复用；
- 15–90 秒文案门禁与原文保护；
- 内容、声音、视觉和表演四类导演计划；
- 每任务询问是否生成 15 秒低成本预览；
- 9:16、默认 720p、固定镜头的 HeyGen Avatar IV 完整原片；
- 自动原片 QA、绑定具体原片的人工批准；
- 原片批准后才允许 HyperFrames 后期；
- 可恢复状态、幂等检查、额度保护、最终 QA 和归档；
- 测试、dry-run、安装及实际生产交付。

## 2. 明确约束

### 2.1 唯一实时供应商通道

实时付费动作只允许调用已安装 HeyGen App 的 OAuth 工具。禁止：

- MiniMax 或其他 TTS/声音克隆供应商；
- `HEYGEN_API_KEY`、`MINIMAX_API_KEY` 或任何 API Key；
- 直连 `api.heygen.com`；
- `curl`、自写 HTTP 客户端或 provider payload 提交；
- 为了上传本地媒体而静默回退到 API；
- 未经确认消耗套餐额度。

本地代码只生成计划、App 动作参数、状态和 QA 结果，不发网络请求。HeyGen App 自己负责 OAuth、套餐权益、任务提交、轮询和结果读取。

### 2.2 套餐额度

每个可能消耗额度的动作前，Skill 先用 HeyGen App 读取当前用户和订阅信息，并检查已有可复用资源。账户信息或剩余额度不可读取时：

- 不回退 API；
- 不声称额度充足；
- 在用户已经明确要求执行本次付费动作时，可以继续，但必须先说明额度数字未能验证；
- 克隆、预览、完整原片和重新生成分别视为独立额度动作。

本设计接受用户当前“按已连接付费账户继续开发”的指示，但实现和测试阶段不实际消耗额度。

### 2.3 本地媒体边界

- `老板音频.mp3` 可作为 HeyGen App `clone_voice` 的内联音频输入。
- HeyGen App 的头像创建只接受 HTTPS 或已有 `asset_id` 时，不允许用 API 上传本地照片。
- 优先复用账户中已经存在且经过用户确认的私人头像组。
- 若目标账户没有对应头像，Skill 停在一次性设置门禁，请用户在 HeyGen 网页/App 手工上传照片，或提供已有 `asset_id/HTTPS`；完成后继续自动流程。

## 3. 资产模型

### 3.1 声音资产

`声音1` 的注册记录至少包含：

- `provider: heygen-app`；
- HeyGen `voice_id`；
- 克隆状态必须为 `complete`；
- 中文语言标记；
- 原始授权音频的本地路径和 SHA-256 指纹；
- 授权状态严格为布尔值 `true`；
- 最近验证时间；
- 语音合成兼容能力，例如是否支持 HeyGen Speech/SSML。

原始音频不复制进 Skill 包，临时 URL 不写入状态。

### 3.2 身份资产

`图片1` 的注册记录至少包含：

- `provider: heygen-app`；
- 稳定的 `avatar_group_id`；
- 身份母图本地路径和 SHA-256 指纹；
- 授权状态严格为布尔值 `true`；
- `business-human-1` 表演档案；
- 默认画幅和允许的手部拓扑；
- 最近验证时间。

`look_id/avatar_id` 是运行时资源，不作为稳定主键。每个任务生成前从 `avatar_group_id` 重新列出 look，选择符合 9:16 和 Avatar IV 能力的 look，并把本次解析结果记录在任务状态中。

### 3.3 未来别名

默认资产是 `声音1`＋`图片1`，但注册表允许新增 `声音2`、`图片2`。每任务可通过受信参数选择其他已授权别名；普通 overrides 不得伪造 `voice_id`、`avatar_group_id`、授权状态或供应商字段。

## 4. 一次性 HeyGen 身份设置

### 4.1 声音克隆

当 `声音1` 没有完整 HeyGen `voice_id` 时：

1. 验证用户已确认声音授权；
2. 对 `老板音频.mp3` 计算指纹；
3. 显示本次会创建一项 HeyGen 克隆声音并可能消耗套餐额度；
4. 用户确认后调用 HeyGen App `clone_voice`，名称为可识别的中文业务名称；
5. 用 `get_voice` 轮询到 `complete`；
6. 验证中文和 Speech/SSML 兼容性；
7. 把 `voice_id` 绑定为 `声音1`。

若已有同名、同指纹且完整的私人克隆声音，优先复用，不重复克隆。

### 4.2 数字人身份

当 `图片1` 没有稳定的 HeyGen `avatar_group_id` 时：

1. 先列出账户内私人头像组并展示候选预览；
2. 若已有与授权肖像匹配的组，由用户确认后绑定；
3. 若没有，要求用户在 HeyGen 网页/App 完成一次本地照片上传或提供已有 `asset_id/HTTPS`；
4. 使用 HeyGen App 创建 Photo Avatar；
5. 必要时完成 HeyGen consent；
6. 轮询训练完成并确认 preview 可用；
7. 保存稳定 `avatar_group_id`，不把临时 look URL 写入状态。

## 5. 每任务规划

### 5.1 文案与时长

- 文案是必填输入。
- 估算时长必须在 15–90 秒范围内，边界包含 15 和 90。
- 未经用户确认不得改写原文。
- 超出范围时返回 `needs_script_confirmation` 和缩短/扩展建议，不创建付费任务。
- 内容导演产生 hook、question、warning、steps、contrast、explanation、conclusion 等语义节拍。

### 5.2 声音导演

声音身份保持为选中的 HeyGen 克隆音色，表达参数按文案变化：

- 语速采用 `deliberate / measured / natural / brisk` 相对等级；
- 问句、警示、步骤、转折和结论分别规划停顿、重音和有限情绪；
- 相邻节拍的速度变化不超过一级；
- 原文字符顺序保持不变；
- 输出 HeyGen SSML 计划，而不是 MiniMax 分段 payload。

执行时优先用 HeyGen App `create_speech` 对整篇 SSML 一次合成，获得完整音频 URL、时长和词级时间轴。若所选克隆音色不支持 Speech/SSML，流程停止并要求解决音色兼容性；不自动换声音，也不静默退回 API。

### 5.3 视觉导演

视觉导演继续按文案和用户覆盖规划穿搭、背景、景别、画幅和姿态，但输出目标是 HeyGen 头像 look 选择/创建要求，而不是调用独立图像供应商。

- 身份由稳定 `avatar_group_id` 保持；
- 穿搭、背景和景别可以随任务变化；
- 默认 9:16、720p、固定镜头；
- 默认中景、一手锚点＋一手主表达、嘴部无遮挡；
- 近景无手时禁止凭空生成手臂；
- 如果现有 look 不满足任务要求，创建新 look 属于独立套餐动作，必须先确认。

### 5.4 表演导演

保留 `business-human-1` 四通道计划：

- 面部：直视为主，眉眼和嘴角随语义微调；
- 头部：小幅偏头、点头和回正，禁止钟摆式持续晃动；
- 手势：准备、强调、可选停留、回位、冷却；
- 身体：稳定躯干、自然呼吸、有限前倾和回正。

动作由语义和实际词级时间轴驱动，不包含固定秒级编舞。相邻节拍避免重复主手势。手部交叠或不可见时，自动把表达转移到面部、头部和身体。

## 6. HeyGen 套餐内执行

### 6.1 预览选择

规划完成后，每任务必须询问是否需要 15 秒低成本预览：

- 选择值写入 `task.json`；
- 状态转换为 `preview_choice_recorded`；
- “否”直接进入完整音频/原片准备；
- “是”会创建独立预览音频和预览视频，可能消耗套餐额度；
- 预览批准永远不等于完整原片批准。

### 6.2 完整音频

1. 检查选中 `voice_id` 已完成并可用于 Speech/SSML；
2. 用声音导演产出的 SSML 调用 HeyGen App `create_speech`；
3. 保存音频 artifact ID、内容指纹、时长和词级时间轴；
4. 不把临时签名 URL写入长期状态；
5. 同一内容指纹和音色已有成功音频时直接复用。

### 6.3 Avatar IV 原片

1. 从 `avatar_group_id` 重新解析竖屏 look；
2. 用 `get_avatar_look` 确认训练完成、画幅和支持的引擎；
3. 只有支持 Avatar IV 的 Photo Avatar look 才能继续；
4. 在主会话完成 Frame Check 和 motion prompt；
5. 调用 HeyGen App `create_video_from_avatar`，输入完整音频 URL、9:16、720p、语义动作提示和适度 expressiveness；
6. 记录 HeyGen `video_id` 并用 `get_video` 轮询；
7. 不使用 script TTS，不让 Video Agent重写原文；
8. 不调用任何 HeyGen HTTP endpoint。

motion prompt 只描述稳定镜头、面部/头部/手势/身体原则、回位和拓扑降级，不包含绝对时间戳，也不重复文案正文。

## 7. 原片审批和 HyperFrames

完整原片完成后执行自动 QA：

- 文件可解码、9:16、默认 720p、音轨完整；
- 时长与音频一致，首尾无截断；
- 中文口型、眼镜、脸部、手指和肢体结构正常；
- 镜头稳定，头动非周期性；
- 手势与语义相符并完整回位；
- 无凭空生成的手臂或异常手指。

进入 HyperFrames 前必须同时满足：

- `artifacts.raw_video.kind == full_raw`；
- 完整原片 SHA-256 已保存；
- `qa_passed is true`；
- HeyGen `video_id` 已保存；
- `approval.raw is true`；
- reviewer、批准时间、证据引用存在；
- 批准指纹与完整原片指纹完全一致。

任何预览确认、付费动作确认、自动 QA、静默、模糊回复或裸 `approval.raw=true` 都不能越过门禁。

通过后才调用 HyperFrames 插件完成字幕、标题、可选 BGM、品牌包装和最终渲染。HyperFrames 不生成或替换数字人原片。

## 8. 状态与恢复

建议状态顺序：

```text
created
-> planned
-> preview_choice_recorded
-> assets_ready
-> audio_ready
-> raw_rendering
-> raw_qa
-> awaiting_raw_approval
-> post_production
-> final_qa
-> complete
```

恢复规则：

- 每项套餐动作提交前检查已有 HeyGen resource ID 和内容指纹；
- 声音克隆、语音合成、预览视频、完整原片分别幂等；
- 轮询或下载失败只恢复当前阶段，不重新提交已成功的额度动作；
- 重新生成必须改变输入或得到用户确认；
- 状态不保存 API Key、Authorization、完整请求头或临时签名 URL；
- 旧 MiniMax 状态只迁移安全的授权别名和本地指纹，不把 MiniMax provider ID 当作 HeyGen voice ID；
- 旧状态保留在原文件或精确字节备份中，新状态不嵌入未知 legacy 值。

## 9. 代码与文档改造

### 9.1 保留

- 内容、视觉和表演导演；
- 15–90 秒规划器和 CLI；
- 受信资产别名与严格授权；
- 原片批准证据门禁；
- HyperFrames 顺序；
- dry-run、原子写入、严格 JSON 和无秘密测试。

### 9.2 替换

- 删除 MiniMax 运行时、字段、文档和环境变量；
- 用 HeyGen SSML 适配器替代 MiniMax payload 构建；
- 用 HeyGen App 动作计划替代 direct HeyGen HTTP payload；
- 注册表从 MiniMax `provider_voice_id` 迁移为 HeyGen `voice_id`；
- 身份记录从单张本地图片主键升级为 HeyGen `avatar_group_id`；
- README、SKILL、openai.yaml、framework、checklists 和 facts 全部统一为 HeyGen App 套餐路线。

### 9.3 不保留的兼容承诺

- 不保证旧 MiniMax voice ID 可直接工作；
- 不保留 direct API payload builder 作为实时后门；
- 不在用户明确要求“无 API”后提供 API Key 回退；
- 不承诺 HeyGen App 无法读取的本地照片可自动上传。

## 10. 测试策略

### 10.1 无额度单元测试

- 注册表默认 `声音1/图片1` 与未来别名；
- 严格授权、provider 字段和 ID 类型；
- 文案原文重构、15/90 秒边界；
- HeyGen SSML 转义、局部语速/停顿/重音和一次性合成动作；
- App 动作参数中无 API Key、HTTP endpoint、Authorization 或签名 URL；
- Avatar look 重新解析和 Avatar IV 能力门禁；
- 四种手部拓扑和 motion prompt；
- 可选预览、额度动作确认和幂等恢复；
- 完整原片批准证据和 HyperFrames 门禁；
- 状态迁移不会把 MiniMax ID 冒充 HeyGen ID。

### 10.2 dry-run 场景

1. 提问＋警示，无穿搭覆盖；
2. 步骤＋CTA，深蓝西装和科技办公室覆盖；
3. 双手交叠的源图；
4. 近景无手；
5. 未来 `声音2/图片2`；
6. 超过 90 秒文案；
7. 不需要预览；
8. 需要预览但拒绝第二次付费重试。

### 10.3 套餐内集成验证

只有在用户再次明确确认消耗额度后才运行：

1. 读取账户订阅；
2. 复用或创建 `声音1`；
3. 复用或绑定 `图片1`；
4. 生成一次短 SSML 语音；
5. 生成一次 15 秒 Avatar IV 预览；
6. 下载并 QA；
7. 不自动进入完整原片或 HyperFrames。

## 11. 完成标准

- 代码、测试、Skill 和安装副本中无 MiniMax 运行路线；
- 实时操作只调用 HeyGen App 和 HyperFrames 插件；
- 不需要或读取任何 API Key；
- `声音1` 是授权的 HeyGen 克隆声音并可长期复用；
- `图片1` 是稳定 HeyGen avatar group，look 每次重新解析；
- 声音节奏随文案变化且原文不被改写；
- 头部、表情、手势和身体由语义触发并自然回位；
- 每任务询问预览但不强制生成；
- 完整原片批准前 HyperFrames 不可达；
- 失败恢复不会重复消耗套餐额度；
- 全量测试、Skill 验证、dry-run、秘密扫描和安装验证通过。
