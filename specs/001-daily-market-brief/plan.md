# Implementation Plan: A股开盘核心新闻聚合研究 Skill

**Branch**: `001-add-core-news-skill` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-daily-market-brief/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

在 `.github/skills/daily-market-brief/` 下创建一个自包含的 Python Skill，用于按交易日生成 A 股盘前核心新闻聚合简报。首轮交付以“关键模块先出临时版、完整流程含 review 在 90 分钟内完成”为约束，优先落地稳定的 CLI、配置驱动范围控制、结构化中间结果、正式报告与缺口标记。

任务拆分上采用“全故事覆盖、MVP 先落 US1”的方式：保留 US2 和 US3 的后续交付面，但不让长期运营与稳定性工作阻塞第一版可运行日报链路。

## Technical Context

**Language/Version**: Python 3.10+，默认在 conda 环境 `legonanobot` 中执行  
**Primary Dependencies**: `PyYAML`、`requests`、`feedparser`、`pytest`、`tushare`、`akshare`，以及标准库 `argparse`、`dataclasses`、`json`、`pathlib`、`logging`  
**Storage**: 本地 YAML 配置、JSON 中间结果/缓存、Markdown 最终报告、规范化示例配置文件  
**Testing**: `pytest`（unit/contract/integration）+ 跨平台 Python 验证入口 `src/validate_daily_run.py` + POSIX shell wrapper `validate-daily-run.sh`  
**Target Platform**: macOS、Linux、Windows 本地命令行环境  
**Project Type**: `.github/skills/daily-market-brief/` 下的自包含 Skill + Python CLI  
**Performance Goals**: 单次完整流程覆盖数据拉取、处理、报告输出与人工 review 交接，整体在 90 分钟内完成；最终报告高光主题不超过 5 条、总板块不超过 10 个、单板块摘要控制在 60 个中文字符内  
**Constraints**: 正式输出默认仅依赖生产源；必须支持配置驱动范围调整；缺失来源不得阻断整份报告；不得写入本机绝对路径、凭据或 IDE 元数据；临时版是流程编排能力而非单独 SLA  
**Scale/Scope**: 5 个分析模块、每交易日 1 份独立报告、每模块保留结构化中间产物，并对核心跟踪清单逐项返回覆盖状态

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Portability gate: PASS. 通过 `src/utils/platform_compat.py` 统一路径、shell、subprocess 与输出目录行为；Windows 不依赖 bash 特性，必要时提供 Python fallback。  
- Setup gate: PASS. 默认复用仓库既有 `legonanobot` conda 环境，以 `requirements.txt + config.example.yaml` 提供最小安装路径。  
- Opencode validation gate: PASS. 跨平台验证命令定义为 `pytest .github/skills/daily-market-brief/tests/ -v`、`conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py --help`、`conda run -n legonanobot python .github/skills/daily-market-brief/src/validate_daily_run.py`；macOS/Linux 额外提供 `./.github/skills/daily-market-brief/validate-daily-run.sh` 作为包装器。提交前将命令与结果记录到 [remediation-log.md](./remediation-log.md)。  
- Reproducibility gate: PASS. CLI 参数、配置结构、模块 JSON Schema 与报告结构契约都将固定，且“部分成功但可出报告”的退出语义会显式定义。  
- Hygiene and privacy gate: PASS. 仅提交脱敏示例配置；`.gitignore` 排除缓存、日志、临时结果；不允许凭据、本机路径或 IDE 产物进入仓库。

## Project Structure

### Documentation (this feature)

```text
specs/001-daily-market-brief/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
.github/skills/daily-market-brief/
├── SKILL.md
├── README.md
├── requirements.txt
├── .gitignore
├── validate-daily-run.sh
├── config/
│   ├── config.example.yaml
│   ├── tracking-lists.yaml
│   └── execution-phases.yaml
├── docs/
├── src/
│   ├── main.py
│   ├── validate_daily_run.py
│   ├── aggregator.py
│   ├── models/
│   ├── modules/
│   ├── sources/
│   └── utils/
└── tests/
    ├── contract/
    ├── integration/
    ├── unit/
    └── fixtures/mock_data/
```

**Structure Decision**: 采用“自包含 Skill 目录”而不是并入现有 Python package。这样可与仓库中现有 Skill 组织方式保持一致，降低对现有 MCP 和分析模块的包结构耦合，同时让配置、脚本、测试与文档围绕同一入口收敛。

## Complexity Tracking

当前无需为宪法例外开口子。复杂度风险主要来自任务切分而非架构本身，应通过收敛首轮交付边界而不是增加技术抽象来处理。

## Phase 0 Research Focus

- 运行时基线：确定 Python 3.10+、`legonanobot` conda 环境与生产源依赖组合。
- 输出契约：确定 CLI 入口、模块结果 Schema、聚合报告 Schema 与 Markdown 报告结构。
- 交付边界：把“单次稳定产出盘前报告”与“长期稳定性/运营观测”拆开，避免首轮计划范围失控。

## Phase 1 Design Outputs

- [research.md](./research.md)：记录技术选型与 MVP 范围决策。
- [data-model.md](./data-model.md)：定义运行任务、模块结果、配置快照、主题高光与聚合报告实体。
- [contracts/](./contracts/)：定义 CLI、模块输出和聚合报告的外部接口契约。
- [quickstart.md](./quickstart.md)：定义本地 setup、运行和验证入口。

## Post-Design Constitution Re-Check

- Portability: PASS，接口与目录设计未引入平台绑定路径。
- Setup: PASS，快速开始仍然只依赖 conda 环境与示例配置。
- Validation: PASS，已明确命令与证据记录位置。
- Reproducibility: PASS，契约文件将约束 CLI 与输出结构。
- Hygiene: PASS，脱敏配置与忽略规则已纳入计划。

## Task Plan Rationality Review

- 结论：任务需要覆盖 US1、US2、US3 三个用户故事，但 MVP 实施顺序应停在 US1 完整跑通和验证闭环。
- 建议保留在 MVP 的核心能力：基础目录/配置/模型/日志/缓存、关键数据源接入、单次完整流程、阶段性报告、缺口标记、对象级覆盖状态、基础 contract/integration tests。
- 建议在 US2/US3 处理的能力：自动/人工边界沉淀、配置维护指南、范围扩展回归验证。
- 建议后移到 post-MVP backlog 的能力：20 个交易日稳定性验证、运营指标沉淀、复杂跨模块冲突检测、全量去重优化、Windows 专项扩展文档。
- 量化验收应以用户已确认口径为准：完整流程 90 分钟内完成；高光主题不超过 5 条；整篇报告不超过 10 个板块；单板块摘要不超过 60 字；SC-003 分子只统计 `covered`、`no_new`、`source_missing` 三类业务状态，`list_error` 单独审计，`disabled` 不计入分母。
