---
name: daily-market-brief
description: 'Generate an A-share pre-open daily market brief with staged publication, structured JSON artifacts, Markdown output, and explicit coverage status for tracked objects.'
argument-hint: 'Provide the trading date, config path, stage preference, and optional module subset.'
---

# Daily Market Brief

把多个盘前信息源汇成一份结构化、可审阅、可补修订的日报。

## 何时使用

- 需要为某个交易日生成盘前新闻聚合简报。
- 需要先给出 temp 版，再在后续补 final 版。
- 需要对社媒账号、研报机构、大宗商品跟踪对象输出显式覆盖状态。
- 需要把结果落成 JSON 与 Markdown，给后续 review 或二次处理使用。

## 输入要求

- 交易日，格式 `YYYY-MM-DD`。
- 配置文件路径，通常是 `config/local.yaml`。
- 可选 stage：`auto`、`temp`、`final`。
- 可选模块子集：`us_market`、`media_mainline`、`social_consensus`、`research_reports`、`commodities`。

## 工作流

1. 先加载并校验配置，确认关键模块、时间窗口和核心跟踪清单不为空。
2. 按固定顺序运行模块，先跑关键模块，再跑补充模块。
3. 关键模块达标后允许生成 temp 版报告。
4. 所有可运行模块完成后生成 final 版报告，并保留 temp/final 之间的修订关系。
5. 每个模块都要输出结构化 JSON，中间错误不能静默吞掉。

## 输出要求

- 结构化模块结果写入 `tmp/<trade-date>/module-results/`。
- 聚合 JSON 与 Markdown 写入 `tmp/<trade-date>/report/`。
- 报告高光不超过 5 条，板块不超过 10 个，每板块摘要不超过 60 个中文字符。

## Staged Publication 规则

- `us_market` 和 `media_mainline` 是 temp 版的关键模块。
- 非关键模块失败时可以继续生成 partial 报告，但必须清楚标记缺口。
- `--strict` 模式下，任何启用模块失败都要升级为非零退出。

## 人工审核边界

- `social_consensus` 与 `research_reports` 出现异常旗标时进入 `review_required`。
- 自动流程负责拉取、聚合、格式化和缺口标注。
- 人工 review 负责判断争议主题、迟到来源和异常证据是否需要修订 final 版。

## Operator Expectations

- 先看 temp：判断关键模块主线是否足够支持盘前动作。
- 再看 final：决定 non-critical 模块里哪些信息值得提升。
- 最后看 coverage：决定 tracking lists 是否需要扩缩容。

## Handoff Flow

1. CLI 或 agent 触发执行。
2. 系统先生成 temp 报告。
3. 剩余模块收敛后生成 final 报告。
4. 操作者只对 `review_required`、`source_missing` 和高影响主题做人工复核。