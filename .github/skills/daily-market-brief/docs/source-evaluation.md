# Source Evaluation

## 分层原则

首轮正式输出只走 production tier。exploration tier 只保留在评估表里，不直接进入 temp/final 报告。

## 关键模块默认值

- `us_market`：critical，优先进入 temp 版
- `media_mainline`：critical，优先进入 temp 版
- `social_consensus`：non-critical，可补充 final 或触发人工 review
- `research_reports`：non-critical，可补充 final 或触发人工 review
- `commodities`：non-critical，用来补强板块和风险背景

## 当前来源策略

### us_market

- 默认层级：production
- 当前实现：优先读取 mock fixtures；无 mock 时尝试 RSS 聚合
- 风险：RSS 可用性和时效性不稳定
- fallback：标记为 `source_missing`，不阻断整份报告

### media_mainline

- 默认层级：production
- 当前实现：优先读取 mock fixtures；无 mock 时尝试 RSS 聚合
- 风险：财经媒体 RSS 结构可能变化
- fallback：标记为 `source_missing`，不阻断整份报告

### social_consensus

- 默认层级：production
- 当前实现：优先读取 mock fixtures；无 mock 时仅对 HTTP 型 tracking feeds 做轻量拉取
- 风险：公开 feed 覆盖不足，容易出现 `no_new` 或 `source_missing`
- fallback：保留对象级覆盖状态，必要时转人工 review

### research_reports

- 默认层级：production
- 当前实现：优先读取 mock fixtures；无 mock 时仅对 HTTP 型 tracking feeds 做轻量拉取
- 风险：机构来源结构差异大，稳定性不一
- fallback：对象级状态保留，允许 final 版补修订

### commodities

- 默认层级：production
- 当前实现：优先读取 mock fixtures；无 mock 时保守降级为 `source_missing`
- 风险：符号型来源尚未绑定稳定 live adapter
- fallback：在报告中显式标注缺口，不影响关键模块先行发布

## 结论

当前版本已经满足 MVP 要求：

- 正式输出默认只依赖 production tier
- 关键模块先行 temp 发布
- 非关键模块缺失不阻断 final/partial 报告
- 每个配置驱动对象都有显式覆盖状态，不会静默丢失