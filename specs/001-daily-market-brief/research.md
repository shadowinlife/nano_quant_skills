# Research: A股开盘核心新闻聚合研究 Skill

**Date**: 2026-04-29  
**Scope**: Resolve the technical context and convert the current roadmap into measurable MVP delivery gates.

## Decision 1: Runtime Baseline

**Decision**: Use Python 3.10+ inside the existing `legonanobot` conda environment as the default runtime.

**Rationale**:
- The repository already standardizes Python execution around `legonanobot`.
- Existing Python modules in this repo target Python 3.10+, which keeps dependency resolution and local validation aligned.
- A single runtime baseline reduces cross-platform debugging cost during the first rollout.

**Alternatives considered**:
- Python 3.11 only: rejected because it adds avoidable version skew relative to the existing repo baseline.
- Per-feature virtualenv: rejected because it increases setup friction for open-source users and duplicates environment management.

## Decision 2: Packaging and Layout

**Decision**: Implement the feature as a self-contained skill directory under `.github/skills/daily-market-brief/`.

**Rationale**:
- This matches the repository's existing pattern of keeping skill documentation, config, scripts, and tests together.
- It avoids coupling this feature to the package layout of `nano-search-mcp` or other top-level modules.
- It keeps the CLI, config files, validation script, and fixtures colocated for simpler maintenance.

**Alternatives considered**:
- New top-level Python package: rejected because the feature is primarily a skill workflow plus CLI, not a reusable library boundary.
- Extending `nano-search-mcp`: rejected because MCP service code and daily-brief orchestration solve different problems and should evolve independently.

## Decision 3: Formal Source Tier for MVP

**Decision**: Formal output in MVP uses only production-tier sources: `tushare`, `akshare`, `feedparser`, and standard RSS-style feeds. Exploration sources remain documented but disabled by default.

**Rationale**:
- This preserves the D2 layered-source decision while keeping the first release stable.
- Experimental scrapers create the highest maintenance and policy risk, which does not help first-pass delivery.
- Formal output must be reproducible; stable APIs and feed formats are more defensible than custom scraping.

**Alternatives considered**:
- Enable custom scrapers in MVP: rejected because availability and maintenance risk are too high.
- Use only one provider for every module: rejected because no single provider reliably covers all five module types.

## Decision 4: Critical Modules and Staged Publication

**Decision**: `us_market` and `media_mainline` are the critical modules for temporary publication. `social_consensus`, `research_reports`, and `commodities` can revise or enrich the report later.

**Rationale**:
- These two modules are the least configuration-heavy and most directly tied to broad pre-open market context.
- They can produce a useful temporary brief even when slower modules are still running or awaiting review.
- This keeps D1 meaningful without forcing a separate MVP time limit for temp versus final output.

**Alternatives considered**:
- All five modules marked critical: rejected because it removes the value of staged publication.
- Only media marked critical: rejected because overseas market context is too important to drop from the first publishable slice.

## Decision 5: Interface Contracts and Artifact Types

**Decision**: Each module emits structured JSON conforming to a schema; the aggregator emits both structured JSON and a Markdown report; the CLI contract explicitly defines partial-success semantics.

**Rationale**:
- Contract tests in the current roadmap already assume stable output shapes.
- Structured intermediate artifacts make failures and missing-source states auditable.
- A partial-success exit contract is required so missing noncritical sources do not incorrectly fail the entire workflow.

**Alternatives considered**:
- Markdown-only outputs: rejected because tests and downstream review need machine-readable intermediate results.
- Hard fail on any missing source: rejected because it violates the graceful-degradation requirements in the spec.

## Decision 6: Quantified MVP Acceptance

**Decision**: The MVP acceptance gate is the user-confirmed full workflow target: data fetch, processing, report generation, and review handoff complete within 90 minutes. The output must contain no more than 5 top highlights, no more than 10 sections, and each section summary must stay within 60 Chinese characters.

**Rationale**:
- The user explicitly accepted a 90-minute end-to-end window for the full process.
- The readability constraints convert a vague “15 minutes readable” statement into directly testable report-shape rules.
- No separate temp-report SLA is enforced in MVP because the user did not confirm one; temp output remains a sequencing mechanism rather than a standalone acceptance gate.

**Alternatives considered**:
- Separate temp/final SLAs now: rejected because the user did not confirm a split target.
- Keep “15 minutes readable” as the only criterion: rejected because it is too subjective to test reliably.

## Decision 7: Coverage Metric and Roadmap Split

**Decision**: Coverage is measured against enabled core tracking items, not just module-level completion. Every enabled item must end in one of `covered`, `no_new`, `source_missing`, or `list_error`; SC-003 attainment counts only the first three business states, while `list_error` is audited separately and `disabled` items are excluded from the denominator. Tasks for 20-day uptime, operational metrics, and advanced cross-module heuristics remain post-MVP.

**Rationale**:
- The user selected object-level coverage as the correct denominator for SC-003.
- This makes config changes auditable and directly supports the maintenance story.
- The current roadmap mixes first-pass delivery with long-horizon reliability work; separating them reduces delivery risk without lowering the functional bar for MVP.

**Alternatives considered**:
- Module-level coverage only: rejected because it hides whether configured accounts/institutions/commodities were actually evaluated.
- Keep every roadmap task in MVP: rejected because it overweights operational maturity before first end-to-end delivery exists.

## Decision 8: Validation Evidence Location

**Decision**: Store pre-commit validation evidence in `specs/001-daily-market-brief/remediation-log.md` until the feature has its own persistent operational log location.

**Rationale**:
- The file already exists in the feature spec area and is suitable for design-phase evidence capture.
- It keeps validation records close to the planning artifacts.
- It avoids introducing an implementation-time path before the skill directory exists.

**Alternatives considered**:
- Store evidence only in terminal history: rejected because it is not durable or reviewable.
- Create a new evidence path now under the future skill directory: rejected because the implementation tree does not exist yet.

## Resulting MVP Boundary

- Keep in MVP: foundational utilities, config baseline, core source adapters, all five module entry points, staged aggregation, object-level status reporting, contract tests, one full integration path.
- Move to post-MVP unless needed by implementation evidence: advanced conflict detection, advanced deduplication, 20-day uptime simulation, operational metrics, and Windows-specific companion docs beyond the minimal validation fallback note.

## Decision 9: Preflight Exit Semantics

**Decision**: 运行时自检失败使用 `exit_code=4`，与 `exit_code=3`（关键模块未达发布）严格互斥；stderr 首行以固定前缀 `PREFLIGHT_FAIL: <comma-separated missing items>` 输出。

**Rationale**:
- 运维脚本/CI 按退出码路由最可靠；错误信息依赖 stderr 文本匹配会随语言、本地化、额外换行走样。
- exit_code=4 在现有 `0/2/3` 上补齐，与原“内部错误”语义的并陈位可使用。内部错误如仍需表达，可后续预留 5。

**Alternatives considered**:
- 统一 exit_code=3 + 靠 stderr 文本分流：拒绝，不可靠。
- 十位段退出码（10/11/12）：拒绝，过度分类产生与 shell “重要退出码”约定冲突。

## Decision 10: Trade Date Tolerance

**Decision**: 请求目标日期与数据源返回交易日期偏差超过 5 个日历日时，record MUST 写入 `previous_session_gap_days` 字段并在报告中渲染“行情滑后”提示。

**Rationale**:
- 5 日同时覆盖周末 + 单一节假日的常规缺口，不会在正常场景误报。
- 超出 5 日多发生于长假后第一个交易日，此时人工复核价值高于隐藏偏离。

**Alternatives considered**:
- 严格按交易日历：拒绝，需要额外补入交易所日历与多市场时区处理，超出最小闭环。
- 仅靠 modify_time 不看 trade_date：拒绝，多个提供方 modify_time 与行情日期不一致。

## Decision 11: Module Semantic Guard Behavior

**Decision**: 当模块声明的业务语义标签（语言 / 区域 / 媒体类型）与所有命中源都不一致时，模块状态降为 `review_required`、不参与 temp 关键模块就绪判定，并在报告对应段落首行输出 “⚠️ 语义偏离：模块声明 X，实际命中源 Y” 提示。

**Rationale**:
- 避免“主流财经媒体”模块默默填充英文外媒这类误导。
- review_required 在现有状态枚举中已有，复用减少变更面。

**Alternatives considered**:
- 直接标记 confirmed 并加水印：拒绝，子会让下游译读者仍以为语义正确。
- 直接报 error：拒绝，误将“语义偏离”与“抓取失败”同语义。

## Decision 12: Source Independence Criterion

**Decision**: 两条源被视为“相互独立”当且仅当满足以下三项中任意两项：（1）顶级域名不同；（2）数据获取协议家族不同（RSS feed / 第三方 SDK API / HTTP 抓取分别为独立家族）；（3）数据提供方机构不同。

**Rationale**:
- 仅靠域名差异会把同机构多个接入点（如同家媒体的 RSS 与 API）误判为冗余；仅靠机构不同可能忽略同一 CDN/接入点同时不可达的风险。三项选二是最小使决策可复制。

**Alternatives considered**:
- 顶级域名 + 机构都必须不同：拒绝，过于严苛，MVP 很难获得两份独立机构源。
- 只要三项中任一项成立：拒绝，同机构同协议不同域名会被误判为冗余。

## Decision 13: Run Summary Artifact Location

**Decision**: 运行摘要输出到 `tmp/<trade-date>/run-summary.json`，与 `report.{temp,final}.{json,md}` 同目录；主聚合报告 JSON 以 `run_summary_path` 字段反向引用。

**Rationale**:
- 同目录保证归档原子性（报告与诊断成对打包上传/存档）。
- 反向引用让下游只要拿到报告就能看到诊断文件路径，不需额外约定。

**Alternatives considered**:
- 写入 logs/ 目录：拒绝，与其他运行产物脱贝，难以跨运行对齐。
- 只写 stdout：拒绝，无法持久化复盘。