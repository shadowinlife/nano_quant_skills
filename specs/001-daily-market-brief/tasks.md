# Tasks: A股开盘核心新闻聚合研究 Skill

**Input**: Design documents from `specs/001-daily-market-brief/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/  
**Tests**: 合同测试、单次端到端集成测试和本地 opencode 验证属于 MVP 范围；20 日稳定性与运营监控验证不属于当前执行清单。  
**Format**: `- [ ] [TaskID] [P?] [Story] Description with file path`

---

## MVP Scope

本清单只覆盖首轮可交付范围：

- 能在 `.github/skills/daily-market-brief/` 下跑通一次完整流程。
- 生成结构化中间结果和独立 Markdown 报告。
- 支持关键模块先出临时版、其余模块后补 final 版。
- 报告满足当前量化门槛：高光不超过 5 条，板块不超过 10 个，每板块摘要不超过 60 个中文字符。
- 完整流程按设计目标支持“数据拉取 + 处理 + 报告输出 + review 交接”在 90 分钟内完成。

明确不放入当前执行面的内容：20 个交易日可用性模拟、运营指标沉淀、复杂跨模块冲突检测、增强版去重、Windows 专项扩展文档、生产运维 runbook。

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 创建最小可运行的 Skill 骨架和提交卫生边界

- [X] T001 Create skill directory skeleton at `.github/skills/daily-market-brief/` with `config/`, `docs/`, `src/`, `src/models/`, `src/modules/`, `src/sources/`, `src/utils/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, and `tests/fixtures/mock_data/`
- [X] T002 Initialize dependency baseline in `.github/skills/daily-market-brief/requirements.txt` for `PyYAML`, `requests`, `feedparser`, `pytest`, `tushare`, and `akshare`
- [X] T003 [P] Create repository hygiene guardrails in `.github/skills/daily-market-brief/.gitignore` excluding `tmp/`, `.cache/`, logs, credentials, and machine-local artifacts
- [X] T004 [P] Create `.github/skills/daily-market-brief/README.md` with setup, execution entry points, and artifact layout
- [X] T005 [P] Create `.github/skills/daily-market-brief/SKILL.md` defining the agent-facing workflow, expected inputs, staged publication behavior, and manual review boundary

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 搭建所有 MVP 用户故事共用的配置、契约、CLI 与报告基础设施

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create `.github/skills/daily-market-brief/config/config.example.yaml` with source-tier flags, critical module list, time windows, and tracked object structure
- [X] T007 Create `.github/skills/daily-market-brief/config/tracking-lists.yaml` with MVP core lists for social accounts, research institutions, and commodities
- [X] T008 Create cross-platform path and subprocess helpers in `.github/skills/daily-market-brief/src/utils/platform_compat.py`
- [X] T009 Create YAML parsing and validation in `.github/skills/daily-market-brief/src/utils/config_loader.py` enforcing non-empty core lists, config snapshot versioning, and explicit empty-list errors
- [X] T010 [P] Create structured logging in `.github/skills/daily-market-brief/src/utils/logger.py`
- [X] T011 [P] Create JSON cache/artifact helpers in `.github/skills/daily-market-brief/src/utils/cache_manager.py`
- [X] T012 Create runtime data models in `.github/skills/daily-market-brief/src/models/` for `DailyRunTask`, `TrackingConfig`, `TrackingItem`, `CoverageStatus`, `ModuleResult`, and `AggregatedReport`
- [X] T013 Create report rendering utilities in `.github/skills/daily-market-brief/src/utils/report_builder.py` enforcing section status markers and readability limits from the plan
- [X] T014 Create CLI entry point in `.github/skills/daily-market-brief/src/main.py` implementing the contract in `specs/001-daily-market-brief/contracts/daily-run-cli.md`
- [X] T015 Setup pytest scaffolding and shared mock fixtures in `.github/skills/daily-market-brief/tests/fixtures/mock_data/`
- [X] T016 Create `.github/skills/daily-market-brief/validate-daily-run.sh` plus cross-platform Python fallback `.github/skills/daily-market-brief/src/validate_daily_run.py` to validate env detection, config loading, CLI help, and writable artifact directories

**Checkpoint**: Foundation ready - MVP implementation can proceed without reopening project structure decisions

---

## Phase 3: User Story 1 - 生成开盘前精炼简报 (Priority: P1) 🎯 MVP

**Goal**: 交付一条可独立运行的日报链路，覆盖五个模块、分阶段发布、对象级覆盖状态和缺口标记

**Independent Test**: 使用 mock data 跑通一次完整流程，生成 temp/final JSON 与 Markdown 报告；报告必须满足“<=5 条高光、<=10 个板块、每板块 <=60 字摘要”，并且每个启用跟踪对象都落入 `covered`、`no_new`、`source_missing` 或 `list_error` 之一，其中 SC-003 达标分子只统计前三类业务状态

### Tests for User Story 1

- [X] T017 [P] [US1] Create contract test for module result artifacts in `.github/skills/daily-market-brief/tests/contract/test_module_output.py` against `specs/001-daily-market-brief/contracts/module-result.schema.json`
- [X] T018 [P] [US1] Create contract test for aggregated reports in `.github/skills/daily-market-brief/tests/contract/test_report_format.py` against `specs/001-daily-market-brief/contracts/aggregated-report.schema.json`
- [X] T019 [US1] Create end-to-end integration test in `.github/skills/daily-market-brief/tests/integration/test_full_workflow.py` covering staged publication, partial success, and Markdown artifact generation
- [X] T020 [US1] Create config-driven coverage integration test in `.github/skills/daily-market-brief/tests/integration/test_config_scope_and_status.py` verifying every enabled tracked object yields an explicit status

### Implementation for User Story 1

- [X] T021 [P] [US1] Implement production source adapters for `us_market`, `media_mainline`, and `commodities` in `.github/skills/daily-market-brief/src/sources/us_market_feed.py`, `.github/skills/daily-market-brief/src/sources/media_feed.py`, and `.github/skills/daily-market-brief/src/sources/commodity_feed.py`
- [X] T022 [P] [US1] Implement production source adapters for `social_consensus` and `research_reports` in `.github/skills/daily-market-brief/src/sources/social_feed.py` and `.github/skills/daily-market-brief/src/sources/research_feed.py`
- [X] T023 [P] [US1] Implement `us_market` and `media_mainline` modules in `.github/skills/daily-market-brief/src/modules/us_market.py` and `.github/skills/daily-market-brief/src/modules/media_mainline.py`
- [X] T024 [P] [US1] Implement `commodities`, `social_consensus`, and `research_reports` modules in `.github/skills/daily-market-brief/src/modules/commodities.py`, `.github/skills/daily-market-brief/src/modules/social_consensus.py`, and `.github/skills/daily-market-brief/src/modules/research_reports.py`
- [X] T025 [US1] Implement orchestrator in `.github/skills/daily-market-brief/src/aggregator.py` with critical-module-first temp publication, graceful degradation, and final revision support
- [X] T026 [US1] Implement object-level coverage accounting and section/module status propagation across `.github/skills/daily-market-brief/src/aggregator.py` and `.github/skills/daily-market-brief/src/utils/report_builder.py`
- [X] T027 [US1] Wire CLI execution and artifact persistence in `.github/skills/daily-market-brief/src/main.py` so module JSON, aggregated JSON, and Markdown reports are emitted deterministically per run
- [X] T028 [US1] Document source tiers and critical-module defaults in `.github/skills/daily-market-brief/docs/source-evaluation.md`, and create a structured source assessment matrix in `.github/skills/daily-market-brief/docs/source-assessment.yaml` aligned with the `SourceAssessment` model, including explicit `source_category` values
- [X] T029 [US1] Add focused unit coverage for report readability limits and staged aggregation behavior in `.github/skills/daily-market-brief/tests/unit/test_aggregator.py`

**Checkpoint**: User Story 1 is independently runnable and produces a publishable daily brief artifact set

---

## Phase 4: User Story 2 - 逐步沉淀自动化研究流程 (Priority: P2)

**Goal**: 为五个模块补齐 step-by-step 任务说明、完成标准、自动/人工边界、审核目标、触发条件、退出条件与后续迭代路线

**Independent Test**: 阅读模块规划文档，确认每个模块都能看到目标、输入、输出、依赖、完成标准、自动执行部分、人工介入部分、审核目标和退出条件

### Implementation for User Story 2

- [X] T030 [US2] Create execution-phase mapping in `.github/skills/daily-market-brief/config/execution-phases.yaml` covering module goals, inputs, outputs, dependencies, completion criteria, review objectives, and exit conditions
- [X] T031 [US2] Document module-level automation boundaries, manual review triggers, and operator handoff objectives in `.github/skills/daily-market-brief/docs/module-automation.md`
- [X] T032 [US2] Document phased automation roadmap and future source-hardening path in `.github/skills/daily-market-brief/docs/automation-roadmap.md`
- [X] T033 [US2] Align `.github/skills/daily-market-brief/SKILL.md` and `.github/skills/daily-market-brief/README.md` with the same auto/manual split, operator expectations, and handoff flow

**Checkpoint**: User Story 2 documents the operating model without reopening MVP runtime design

---

## Phase 5: User Story 3 - 基于配置稳定扩展信息覆盖面 (Priority: P3)

**Goal**: 让维护者可以调整配置清单而不改动主流程，并保持统一报告结构

**Independent Test**: 修改 tracking lists 后重新运行流程，输出范围随配置变化，但报告结构、状态字段和产物路径保持稳定

### Implementation for User Story 3

- [X] T034 [P] [US3] Create config update regression test in `.github/skills/daily-market-brief/tests/integration/test_config_update_roundtrip.py` for add/remove tracked items without report-shape regressions
- [X] T035 [US3] Extend `.github/skills/daily-market-brief/src/utils/config_loader.py` to support enabled/disabled flags, core-vs-extended tiers, and stable config snapshot diffs for reruns
- [X] T036 [US3] Extend `.github/skills/daily-market-brief/src/aggregator.py` and `.github/skills/daily-market-brief/src/utils/report_builder.py` so config changes alter scope without changing report contract structure
- [X] T037 [US3] Create maintenance guide in `.github/skills/daily-market-brief/docs/tracking-lists-guide.md` with examples for social accounts, research institutions, and commodities
- [X] T038 [US3] Add scope-maintenance examples to `.github/skills/daily-market-brief/config/config.example.yaml` and `.github/skills/daily-market-brief/README.md`

**Checkpoint**: User Story 3 proves the tracked universe can evolve through config changes rather than code edits

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 用最小但严格的验证闭环确认各故事可交付，并完成提交卫生检查

- [X] T039 [P] Create implementation quickstart in `.github/skills/daily-market-brief/docs/quickstart.md` aligned with `specs/001-daily-market-brief/quickstart.md` and production-source defaults
- [X] T040 Run `pytest .github/skills/daily-market-brief/tests/ -v` and fix failures until all implemented story tests pass
- [X] T041 Run `conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py --help` and confirm CLI contract availability
- [X] T042 Run `conda run -n legonanobot python .github/skills/daily-market-brief/src/validate_daily_run.py` on all platforms, use `./.github/skills/daily-market-brief/validate-daily-run.sh` as a POSIX wrapper on macOS/Linux, and capture pass evidence in `specs/001-daily-market-brief/remediation-log.md`
- [X] T043 Audit `.github/skills/daily-market-brief/` for credentials, local absolute paths, IDE metadata, and temporary artifacts before first commit
- [X] T044 [P] Verify macOS/Linux/Windows behavior notes and the Python validation fallback are documented in `.github/skills/daily-market-brief/README.md` or `.github/skills/daily-market-brief/docs/quickstart.md`

**Checkpoint**: Current implementation slice is validated and safe to review or commit

---

## Phase 7: Iteration Δ — Runtime Reliability & Observability (FR-021~FR-029, SC-006~SC-010)

**Purpose**: 将 2026-04-29 真实数据端到端运行暴露的问题，按 plan.md Phase 0/1 增量、5 项 Clarifications 与新契约 `run-summary.schema.json` 落到运行时代码、测试与文档。所有任务都强化 US1 的可靠性，因此沿用 `[US1]` 标签。

**Pre-requisite**: Phase 1~6 已完成（T001-T044 均为 [X]）

### Contract Tests for Iteration Δ

- [X] T045 [P] [US1] Create contract test for run summary artifacts in `.github/skills/daily-market-brief/tests/contract/test_run_summary_schema.py` validating produced `tmp/<date>/run-summary.json` against `specs/001-daily-market-brief/contracts/run-summary.schema.json`
- [X] T046 [P] [US1] Extend `.github/skills/daily-market-brief/tests/contract/test_module_output.py` with cases asserting `semantic_drift`, `attempted_source_ids` and the new evidence fields (`trade_date`, `previous_session_gap_days`, `semantic_tag`) round-trip against the updated `module-result.schema.json`
- [X] T047 [P] [US1] Extend `.github/skills/daily-market-brief/tests/contract/test_report_format.py` with a case asserting `run_summary_path` is emitted on every aggregated report

### FR-021: Dependency Checking

- [X] T048 [US1] Pin and document explicit minimum versions in `.github/skills/daily-market-brief/requirements.txt` for `feedparser>=6.0.11`, `akshare>=1.18`, `requests>=2.31`, `pyyaml>=6.0`, `jinja2>=3.1`, `jsonschema>=4.21`
- [X] T049 [P] [US1] Implement failure taxonomy enum in `.github/skills/daily-market-brief/src/failure_taxonomy.py` (FR-022) covering `dependency_missing`, `network_timeout`, `http_non_2xx`, `parse_empty`, `source_schema_changed`, `unknown`
- [X] T050 [P] [US1] Implement run summary writer in `.github/skills/daily-market-brief/src/run_summary.py` (FR-027) producing `tmp/<trade-date>/run-summary.json`
- [X] T051 [US1] Implement preflight self-check in `.github/skills/daily-market-brief/src/preflight.py` (FR-021): import-check declared dependencies, return a `PreflightResult`
- [X] T052 [US1] Wire preflight into `.github/skills/daily-market-brief/src/main.py` with `exit_code=4` on failure and `--skip-preflight` debug flag
- [X] T053 [US1] Have `.github/skills/daily-market-brief/src/aggregator.py` call `run_summary.py` and set `run_summary_path`
- [X] T054 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_preflight.py` (10 tests)
- [X] T055 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_failure_taxonomy.py` (7 tests)
- [X] T056 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_run_summary.py` (5 tests)

### FR-023: Semantic Tag Guard

- [X] T057 [US1] Extend `.github/skills/daily-market-brief/src/modules/common.py` to detect semantic drift and populate `ModuleResult.semantic_drift`
- [X] T058 [US1] Update `report_builder.py` to render `⚠️ 语义漂移检测` hint when `semantic_drift` set
- [X] T059 [P] [US1] Add `semantic_tag` declarations to every entry in `.github/skills/daily-market-brief/docs/source-assessment.yaml`
- [X] T060 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_module_semantic_guard.py` (7 tests)

### FR-024: Trade Date Provenance

- [X] T061 [US1] Update `.github/skills/daily-market-brief/src/sources/commodity_feed.py` to populate `EvidenceRecord.trade_date` and `previous_session_gap_days`
- [X] T062 [US1] Render "行情滞后 N 日" hint inline in Markdown section via `report_builder.py`
- [X] T063 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_trade_date_provenance.py` (7 tests)

### FR-025: Placeholder Guard / FR-029: Disabled Reason

- [X] T064 [US1] Extend `config_loader.py` to detect placeholder tokens in tracked items and enforce `disabled_reason` when `enabled=false`
- [X] T065 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_tracking_placeholder_guard.py` (9 tests)

### FR-026: Source Independence

- [X] T066 [US1] Implement source-independence checker in `.github/skills/daily-market-brief/src/utils/source_independence.py` and call it from `aggregator.py`
- [X] T067 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_source_redundancy.py` (8 tests)

### FR-028: Stage Coverage Consistency

- [X] T068 [US1] In `aggregator.py`, ensure `coverage_summary` totals match enabled tracked item count; on mismatch log warning
- [X] T069 [P] [US1] Create `.github/skills/daily-market-brief/tests/test_stage_coverage_consistency.py` (6 tests)

### FR-029: End-to-End Iteration Validation

- [X] T070 [US1] Create iteration-level integration test in `.github/skills/daily-market-brief/tests/integration/test_iteration_runtime_reliability.py` (4 tests)
- [X] T071 [US1] Append "Phase 7 / 2026-04-29 Iteration Δ" entry in `specs/001-daily-market-brief/remediation-log.md`
- [X] T072 [P] [US1] Update `.github/skills/daily-market-brief/README.md` and `docs/quickstart.md` with preflight behavior, exit codes, `--skip-preflight`, run-summary artifact location
- [X] T073 [US1] Add `disabled_reason` to `TrackingItem`, `skip_reason` to `ModuleResult`, enforce in `config_loader.py`, render in `report_builder.py`, unit test in `tests/unit/test_module_status_reason.py`

**Checkpoint**: Iteration Δ delivers FR-021~FR-029 with contract tests, behavior unit tests, and an end-to-end integration test.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion - MVP delivery stop point
- **User Story 2 (Phase 4)**: Can start after Foundational completion, but is more accurate once US1 interfaces stabilize
- **User Story 3 (Phase 5)**: Can start after Foundational completion, but derives most value after US1 config-driven flow exists
- **Polish (Phase 6)**: Depends on the stories you choose to complete in the current iteration

### Within User Story 1

- Contract and integration tests should be created before or alongside implementation and must fail before the corresponding feature is considered complete
- Source adapters precede module implementations
- Module implementations precede aggregator wiring
- Aggregator and report builder behavior must be in place before CLI artifact validation

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational - delivers the first runnable daily brief
- **US2 (P2)**: Can start after Foundational - documents how the workflow should be operated and evolved
- **US3 (P3)**: Can start after Foundational - strengthens config-driven scope evolution on top of the same report contract

### Parallel Opportunities

- T003, T004, and T005 can run in parallel
- T010 and T011 can run in parallel after T008/T009 start shaping shared utilities
- T017 and T018 can run in parallel
- T021 and T022 can run in parallel
- T023 and T024 can run in parallel after the relevant source adapters exist
- T030 and T031 can be developed in parallel once module/result shapes are stable
- T034 can run in parallel with T037 and T038
- T039 and T044 can run in parallel during final validation

---

## Parallel Example: User Story 1

```bash
# Contract tests can be created in parallel
Task: "Create contract test for module result artifacts in .github/skills/daily-market-brief/tests/contract/test_module_output.py"
Task: "Create contract test for aggregated reports in .github/skills/daily-market-brief/tests/contract/test_report_format.py"

# Source adapters can be created in parallel
Task: "Implement production source adapters for us_market, media_mainline, and commodities"
Task: "Implement production source adapters for social_consensus and research_reports"
```

## Parallel Example: User Story 2

```bash
Task: "Create execution-phase mapping in .github/skills/daily-market-brief/config/execution-phases.yaml"
Task: "Document module-level automation boundaries and manual review triggers in .github/skills/daily-market-brief/docs/module-automation.md"
```

## Parallel Example: User Story 3

```bash
Task: "Create config update regression test in .github/skills/daily-market-brief/tests/integration/test_config_update_roundtrip.py"
Task: "Create maintenance guide in .github/skills/daily-market-brief/docs/tracking-lists-guide.md"
```

---

## Implementation Strategy

### MVP-First Sequence

1. Complete Phase 1 to freeze the directory, dependency, and hygiene baseline.
2. Complete Phase 2 so config, models, CLI, report builder, and validation script exist.
3. Complete Phase 3 and stop once one full mock-driven daily workflow passes.
4. Validate and demo at the Phase 3 checkpoint before expanding to US2 or US3.
5. Add Phase 4 and Phase 5 incrementally, then finish with Phase 6 validation.

### Why This Is Smaller Than The Previous Plan

- It keeps all three user stories represented in the plan, so later work stays traceable to the spec.
- It removes long-horizon reliability work from the first execution cycle.
- It keeps all five modules in MVP because they are part of the promised brief, but drops nonessential heuristics such as advanced conflict detection and dedup optimization.
- It treats staged publication as a sequencing feature, not an excuse to split the deliverable into multiple release tracks.

---

## Deferred After MVP

以下内容保留为 post-MVP backlog，不属于当前执行清单：

- 20 个交易日可用性模拟与 90% 可用性验证
- 运营指标沉淀、告警、runbook 和生产值守文档
- 高级聚合启发式：复杂冲突检测、增强版跨模块去重、更多人工复核触发器
- 扩展文档资产：architecture index、coverage matrix、migration guide
