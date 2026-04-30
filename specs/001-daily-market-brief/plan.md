# Implementation Plan: A股开盘核心新闻聚合研究 Skill

**Branch**: `001-add-core-news-skill` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-daily-market-brief/spec.md`

## Summary

向 A 股盘前研究者交付一份独立的、按日生成的核心新闻聚合简报，覆盖五个分析模块（美股热点、主流财经媒体、自媒体共识、研报动态、大宗商品），具备 temp/final 分阶段发布、按对象级跟踪覆盖统计、关键模块多源冗余与运行时可观测性。本轮规划在 T001-T044 已交付的最小闭环之上，吸收首次真实数据端到端运行（2026-04-29，exit_code=0）暴露的问题，把 FR-021~FR-029 与 SC-006~SC-010 落实到运行时自检、源失败分类、模块语义守卫、trade_date 真实性、占位符守卫、源独立性判定、运行摘要 `run-summary.json`、阶段统计一致性等设计层面，使新增条款本身可测试、可复盘。

技术方法：复用既有 Python 3.10+ + `legonanobot` conda 环境与自包含 skill 目录结构，在 fetcher / aggregator / renderer 三层加守卫与可观测性扩展，不引入新一级架构组件；新增的 run-summary 与失败分类作为 contracts/ 中独立 schema 文件治理，并在主报告 JSON 中以 `run_summary_path` 反向引用。

## Technical Context

**Language/Version**: Python 3.10+（统一在 `legonanobot` conda 环境内执行）
**Primary Dependencies**: 已在 requirements 中显式声明并通过 preflight 校验：`feedparser>=6.0.11`、`akshare>=1.18`、`requests>=2.31`、`pyyaml>=6.0`、`jinja2>=3.1`、`jsonschema>=4.21`；`tushare` 仅在显式启用 token 的模块下被导入
**Storage**: 文件型，运行产物落 `.github/skills/daily-market-brief/tmp/<trade-date>/`；配置落 `.github/skills/daily-market-brief/config/local.yaml`（受 .gitignore 保护，仅 example 进库）
**Testing**: pytest（新建 `.github/skills/daily-market-brief/tests/`，覆盖 fetcher 降级、preflight、模块语义守卫、trade_date 真实性、aggregator 关键模块判定、模板渲染）；jsonschema 用于契约验证
**Target Platform**: macOS / Linux / Windows，按 FR-017 提供 POSIX shell 包装与 Python 验证脚本兜底
**Project Type**: 自包含 skill 目录（CLI + 配置 + 模块 + 模板 + 测试 + 契约）
**Performance Goals**: 一次完整运行端到端 ≤ 90 分钟（沿用 SC-001 转化目标）；failed run 的诊断时长 ≤ 5 分钟（SC-007）
**Constraints**: 报告头部 ≤ 5 个 top highlights、≤ 10 个 section、每段摘要 ≤ 60 中文字符；preflight 失败 exit_code=4 与"关键模块未达发布" exit_code=3 严格互斥；trade_date 偏差 > 5 个日历日必须显式标注
**Scale/Scope**: 5 个分析模块、按对象级覆盖统计（核心+扩展跟踪清单）、temp+final 双阶段发布、单运行单聚合报告

## Constitution Check

- **Portability gate**: preflight 自检脚本与所有 fetcher 均使用 Python 标准库 + 跨平台依赖；macOS/Linux 提供 `validate-daily-run.sh` POSIX 包装，Windows 用户直接走 `python validate_daily_run.py`，符合 FR-017。**PASS**
- **Setup gate**: quickstart.md 已定义最小本地启动序列（conda activate + pip + 复制 example 配置），新增 preflight 在 main.py 启动时执行，缺依赖给出明确 `PREFLIGHT_FAIL:` 提示，符合 FR-018。**PASS**
- **Opencode validation gate**: 沿用既有 `validate_daily_run.py` + 新增 `tests/` 单测目录；evidence 写入 `specs/001-daily-market-brief/remediation-log.md`；CI/本地通过判定为 `pytest exit 0` + `validate_daily_run.py exit 0`，符合 FR-019。**PASS**
- **Reproducibility gate**: CLI exit_code 语义在 contracts/daily-run-cli.md 显式枚举（0/2/3/4/5），run-summary.json 提供完整诊断字段；fetcher 在所有声明源失败时仅做 source_missing 降级，不静默吞错，符合 FR-022/FR-026/FR-027。**PASS**
- **Hygiene and privacy gate**: `config/local.yaml`、`tmp/` 已在 `.gitignore`；preflight 不打印 token；run-summary 仅记录 URL 与 HTTP 状态、不持久化响应体；符合 FR-020。**PASS**

无违反项，Complexity Tracking 表保持空。

## Project Structure

### Documentation (this feature)

```text
specs/001-daily-market-brief/
├── plan.md                       # This file
├── research.md                   # Phase 0 research（本轮新增 Decision 9 ~ 13）
├── data-model.md                 # Phase 1 数据模型（本轮新增 RunSummary / FailureClass / SemanticTag）
├── quickstart.md                 # Phase 1 启动手册
├── contracts/
│   ├── aggregated-report.schema.json      # 既有，新增 run_summary_path 字段
│   ├── module-result.schema.json          # 既有，新增 semantic_drift 字段
│   ├── run-summary.schema.json            # 新增：FR-027 运行摘要契约
│   └── daily-run-cli.md                   # CLI exit code 0/2/3/4 + PREFLIGHT_FAIL: 前缀
├── checklists/
│   ├── requirements.md
│   └── progress.md
├── decisions.md
├── remediation-log.md
└── tasks.md                      # 由 /speckit.tasks 生成
```

### Source Code (repository root)

```text
.github/skills/daily-market-brief/
├── SKILL.md
├── README.md
├── requirements.txt              # 新增/更新：显式声明 feedparser/akshare/requests/pyyaml/jinja2/jsonschema
├── config/
│   ├── config.example.yaml       # 进 git
│   ├── local.yaml                # 仅本地，进 .gitignore
│   └── tracking-lists.yaml       # 进 git；含 placeholder 校验关键词
├── src/
│   ├── main.py                   # CLI 入口；启动时调 preflight，按 exit_code 4 中止
│   ├── preflight.py              # 新增：FR-021 运行时自检
│   ├── aggregator.py             # 既有；扩展 stage coverage 一致性、模块语义降级
│   ├── tracking.py               # 既有；扩展 placeholder 守卫（FR-025）
│   ├── run_summary.py            # 新增：FR-027 运行摘要写入器
│   ├── failure_taxonomy.py       # 新增：FR-022 失败分类枚举与映射
│   ├── modules/
│   │   ├── common.py             # 扩展：semantic_tag 比对、status=review_required 路径
│   │   ├── us_market.py
│   │   ├── media_mainline.py
│   │   ├── commodities.py
│   │   ├── social_consensus.py
│   │   └── research_reports.py
│   ├── sources/
│   │   ├── rss.py                # 既有；返回 attempted_sources 元数据
│   │   ├── us_market_feed.py     # 多源冗余（≥ 2 独立源）
│   │   ├── media_feed.py         # 多源冗余（含 akshare fallback）
│   │   ├── commodity_feed.py     # 用真实 trade_date；偏差 > 5 天标 previous_session_gap_days
│   │   ├── social_feed.py
│   │   └── research_feed.py
│   ├── render/
│   │   ├── markdown.py           # 段落首行 ⚠️ 语义偏离提示渲染
│   │   └── templates/
│   ├── validate_daily_run.py     # 调 preflight + dry-run aggregator
│   └── utils/
├── tests/                         # 新增目录
│   ├── test_preflight.py
│   ├── test_failure_taxonomy.py
│   ├── test_module_semantic_guard.py
│   ├── test_trade_date_provenance.py
│   ├── test_tracking_placeholder_guard.py
│   ├── test_source_redundancy.py
│   ├── test_run_summary.py
│   ├── test_stage_coverage_consistency.py
│   └── fixtures/
└── tmp/                          # 运行产物；进 .gitignore
    └── <trade-date>/
        ├── module-results/*.json
        ├── run-summary.json      # FR-027
        └── report/
            ├── report.temp.{json,md}
            └── report.final.{json,md}
```

**Structure Decision**: 沿用既有自包含 skill 目录（research.md Decision 2）。本轮迭代仅新增 `preflight.py`、`run_summary.py`、`failure_taxonomy.py` 与 `tests/` 目录；`contracts/` 新增 `run-summary.schema.json` 一份；既有 schema 仅追加字段不破坏向后兼容。

## Phase 0: Outline & Research（Δ）

研究产物保留在 [research.md](research.md)。本轮迭代基于 Clarifications Session 2026-04-29 的 5 项决策，向 research.md 追加：

- **Decision 9 — Preflight 退出语义**：使用 `exit_code=4` 与 `PREFLIGHT_FAIL:` stderr 前缀（与 exit_code=3 互斥）；备选"统一 exit_code=3 + 错误前缀分流"被拒绝，因为运维脚本难以可靠按内容路由。
- **Decision 10 — Trade Date 偏差阈值**：5 个日历日（覆盖周末 + 单一节假日，长假后强制人工复核）；备选"按交易所日历"被拒绝，依赖额外日历表与时区处理，对最小闭环过重。
- **Decision 11 — 模块语义守卫降级路径**：`semantic_tag` 全失配时降为 `review_required` 并屏蔽 temp 关键模块判定；备选"直接 confirmed 但加水印"被拒绝，因为这与 SC-002 可靠性目标冲突。
- **Decision 12 — 源独立性判定**：三选二（顶级域名 / 协议家族 / 提供方机构）；备选"协议+域名双满足"被拒绝，会把同机构的 RSS+API 误判为冗余。
- **Decision 13 — Run Summary 落地位置**：`tmp/<date>/run-summary.json` 与 report 同目录，主聚合 JSON 加 `run_summary_path` 字段反向引用。

输出：research.md 增补 Decision 9 ~ 13；保持零 NEEDS CLARIFICATION。

## Phase 1: Design & Contracts（Δ）

### 数据模型增量

向 [data-model.md](data-model.md) 追加：

- **新增实体 `RunSummary`**：`run_id`、`generated_at`、`preflight{ok, missing[]}`、`modules[]{module, declared_semantic_tag, declared_sources[], attempted_sources[]{url, protocol, http_status, records, fail_class, semantic_tag}, final_status, semantic_drift{declared, observed, drift_categories[]}}`、`coverage_summary`。
- **新增枚举 `FailureClass`**：`dependency_missing`、`network_timeout`、`http_non_2xx`、`parse_empty`、`source_schema_changed`、`unknown`。
- **新增枚举 `SemanticTag`**（应用于 `SourceAssessment` 与 fetcher 返回的 evidence 元数据）：`language ∈ {zh, en, mixed}`、`region ∈ {cn, us, global, ...}`、`media_type ∈ {newswire, op_ed, market_data, regulator, ...}`。
- **`ModuleResult` 扩展**：新增 `semantic_drift` 对象（与上一致），允许 `status=review_required` 触发 anomaly_flag `semantic_mismatch`。
- **`EvidenceRecord` 扩展**：新增 `trade_date`（行情类）、`previous_session_gap_days`（仅当偏差 > 5 时出现）、`semantic_tag`。
- **`AggregatedReport` 扩展**：新增 `run_summary_path` 字段。
- **`TrackingItem` 扩展（FR-029）**：新增 `disabled_reason` 字段（`enabled: false` 时必填），使维护者无需查阅历史会话即可理解禁用决策。
- **`ModuleResult` 扩展（FR-029）**：新增 `skip_reason` 字段（`status = skipped` 时适用；config-disabled 的模块在运行时映射为 `status=skipped`，`skip_reason` 取 `TrackingItem.disabled_reason` 的值），在报告对应段落内联渲染。

### 契约增量

- **新增 `contracts/run-summary.schema.json`**：JSON Schema Draft-07，与上述 `RunSummary` 实体一一对应，必填字段：`run_id`、`generated_at`、`preflight`、`modules`。
- **`contracts/aggregated-report.schema.json` 增补**：`run_summary_path`（可选 string，仅当文件存在时必填）。
- **`contracts/module-result.schema.json` 增补**：`semantic_drift` 对象（可选）；`status` 枚举增加既有 `review_required` 的语义文档说明（非破坏）。
- **`contracts/daily-run-cli.md` 增补**：
  - exit_code 表格补 `4 = preflight_failed`，与既有 `0 / 2 / 3` 严格互斥；
  - 增加 stderr 约定：preflight 失败时第一行为 `PREFLIGHT_FAIL: <comma-separated missing items>`；
  - 文档化 `--skip-preflight` 仅作为本地调试 escape hatch（不进入 CI 路径）。

### 验证策略

- **契约测试**：`tests/test_contract_schemas.py` 用 jsonschema 对最小样例与边界样例做 round-trip。
- **行为单测**（≥ 8 个）：preflight 缺依赖、preflight 缺配置、failure 分类映射、模块语义守卫降级、trade_date 偏差阈值、tracking 占位符阻断启用模块/告警禁用模块、源独立性判定、stage 覆盖统计一致性。
- **集成测试 1 个**：`tests/test_end_to_end_with_fixtures.py` 用本地 fixture 跑 `main.py --stage auto`，断言 `exit_code=0` 且 `run-summary.json` 字段齐全；故意删除一项依赖再断言 `exit_code=4`。

### Agent Context Update

更新 [.github/copilot-instructions.md](.github/copilot-instructions.md) 中 SPECKIT 块，使其指向本计划文件 `specs/001-daily-market-brief/plan.md`（已为当前路径，仅校验）。

### 重新评估宪章 Gates

新增的 preflight、run-summary、placeholder guard 均强化 Reproducibility 与 Hygiene gate；Portability gate 保持（preflight 仅依赖 importlib + 标准库）。**重新评估通过**，无新增违反项。

## Phase 2: Planning Boundary

依据 speckit 分工，本计划 ENDS HERE。`tasks.md` 由 `/speckit.tasks` 在后续基于本 plan、data-model、contracts、quickstart 增量生成。

## Complexity Tracking

无违反项需要论证。本轮迭代仅在既有目录结构上新增 3 个内聚文件（`preflight.py`、`run_summary.py`、`failure_taxonomy.py`）与 1 个新契约 schema，未引入新一级架构组件、未跨进程边界、未新增持久化层。
