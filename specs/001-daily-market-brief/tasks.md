# Tasks: A股开盘核心新闻聚合研究 Skill

**Input**: Design documents from `/specs/001-daily-market-brief/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories)  
**Format**: `- [ ] [TaskID] [P?] [Story] Description with file path`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic project structure

- [ ] T001 Create SKILL directory structure per implementation plan at `.github/skills/daily-market-brief/`
- [ ] T002 Initialize Python project with conda environment (legonanobot) and pip dependencies in `.github/skills/daily-market-brief/requirements.txt`
- [ ] T003 [P] Setup linting (flake8/pylint) and formatting (black) configuration in `.github/skills/daily-market-brief/`
- [ ] T004 Create `.gitignore` file at `.github/skills/daily-market-brief/` to exclude tmp/, .cache/, *.log, credentials
- [ ] T005 [P] Create initial README.md at `.github/skills/daily-market-brief/README.md` with setup instructions
- [ ] T006 [P] Create SKILL.md definition for Copilot integration at `.github/skills/daily-market-brief/SKILL.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Create configuration schema and YAML template at `.github/skills/daily-market-brief/config/config.example.yaml` defining tracking lists structure (social media, research institutions, commodities, time windows)
- [ ] T007a Create initial tracking-lists.yaml with core lists in `.github/skills/daily-market-brief/config/tracking-lists.yaml` (5-10 core social accounts, 5-10 research institutions, 10-15 commodities) as user-maintainable configuration baseline
- [ ] T008 Create platform compatibility utilities in `.github/skills/daily-market-brief/src/utils/platform_compat.py` for cross-platform path/subprocess handling (macOS/Linux/Windows)
- [ ] T009 Create configuration loader utility in `.github/skills/daily-market-brief/src/utils/config_loader.py` to parse, validate YAML tracking lists, and check for empty/expired tracking lists
- [ ] T010 Create logger utility in `.github/skills/daily-market-brief/src/utils/logger.py` for structured logging across all modules
- [ ] T011 Create cache manager utility in `.github/skills/daily-market-brief/src/utils/cache_manager.py` for local JSON caching of intermediate results
- [ ] T012 Create data model definitions in `.github/skills/daily-market-brief/src/models/` directory with DailyRunTask, ModuleResult, TrackingConfig, AggregatedReport classes
- [ ] T013 Create report builder utility in `.github/skills/daily-market-brief/src/utils/report_builder.py` for markdown report generation and aggregation
- [ ] T014 Setup pytest test infrastructure with fixtures in `.github/skills/daily-market-brief/tests/fixtures/mock_data/`
- [ ] T015 Create cross-platform validation script at `.github/skills/daily-market-brief/validate-daily-run.sh` for local opencode validation before commit
- [ ] T016 Create base CLI/entry point in `.github/skills/daily-market-brief/src/main.py` with argparse for date, config path, and module selection options
- [ ] T016a Create minimal validation script proof-of-concept (`.github/skills/daily-market-brief/validate-daily-run.sh` partial implementation) validating cross-platform shell compatibility and Python env detection to verify design portability (Constitution Gate III checkpoint)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 生成开盘前精炼简报 (Priority: P1) 🎯 MVP

**Goal**: Deliver complete daily news aggregation report covering all five analysis modules with staged publication and config-driven scope

**Independent Test**: Run complete workflow with mock data and verify all-5-modules-enabled report is generated with correct structure, section prioritization, and gap markers within 15 minutes readable time

### Tests for User Story 1

- [ ] T017 [P] [US1] Create contract test for module output schema in `.github/skills/daily-market-brief/tests/contract/test_module_output.py` validating JSON/markdown format
- [ ] T018 [P] [US1] Create contract test for report aggregation format in `.github/skills/daily-market-brief/tests/contract/test_report_format.py`
- [ ] T019 [US1] Create integration test for full daily workflow in `.github/skills/daily-market-brief/tests/integration/test_full_workflow.py` using mock data

### Implementation for User Story 1 - Core Modules (US/Media/Commodities)

- [ ] T020 [P] [US1] Implement US market module in `.github/skills/daily-market-brief/src/modules/us_market.py` (FULL AUTO) analyzing previous trading day US hotspots
- [ ] T021 [P] [US1] Implement media mainline module in `.github/skills/daily-market-brief/src/modules/media_mainline.py` (FULL AUTO) extracting cross-highlighted topics from CN media (max 5)
- [ ] T022 [P] [US1] Implement commodities module in `.github/skills/daily-market-brief/src/modules/commodities.py` (FULL AUTO) tracking commodity prices and regional news
- [ ] T023 [P] [US1] Create data source implementations for core modules: `.github/skills/daily-market-brief/src/sources/us_market_feed.py`, `.media_feed.py`, `.commodity_feed.py` using production sources (tushare/akshare/feedparser per D2 decision); exploration sources documented in docs/source-evaluation.md

### Implementation for User Story 1 - Expanded Modules (Social/Research)

- [ ] T024 [P] [US1] Implement social media consensus module in `.github/skills/daily-market-brief/src/modules/social_consensus.py` (FULL AUTO with quality gate: auto scrape + consensus detection + anomaly-triggered manual review) analyzing past 5 trading days common themes from config-tracked accounts
- [ ] T025 [P] [US1] Implement research reports module in `.github/skills/daily-market-brief/src/modules/research_reports.py` (FULL AUTO with quality gate: auto discovery + relevance scoring + publication date verification + anomaly-triggered manual review) covering domestic and overseas institutions from config
- [ ] T026 [P] [US1] Create data sources for social/research: `.github/skills/daily-market-brief/src/sources/social_feed.py`, `.research_feed.py` using production sources from Phase 2 config

### Implementation for User Story 1 - Aggregation & Publication

- [ ] T027 [US1] Implement aggregator orchestration in `.github/skills/daily-market-brief/src/aggregator.py` coordinating all 5 modules with staged publication strategy (temp report after critical modules complete, revision possible post-manual review) - implements D1 decision
- [ ] T028 [US1] Document critical module definition list and staged report schema in plan/aggregator (e.g., US + Media are critical; Social/Research/Commodities are optional for temp version)
- [ ] T029 [US1] Implement staged publication strategy in aggregator: generate temp report when critical modules complete, allow later revision with additional modules
- [ ] T030 [US1] Add error handling and graceful degradation when individual sources unavailable in aggregator
- [ ] T031 [US1] Add section-level status markers (confirmed/pending/missing) to report in report builder
- [ ] T032 [US1] Implement conflict detection logic in aggregator: flag when same topic appears in multiple modules with conflicting perspectives and mark for manual review
- [ ] T033 [US1] Implement cross-module deduplication algorithm: merge duplicate topics across modules while preserving evidence hierarchy
- [ ] T034 [US1] Implement dynamic scope loading in aggregator: read tracking lists from config (Phase 2) and apply scope filters to each module

### Tests for User Story 1 (Completion)

- [ ] T035 [US1] Implement unit tests for aggregator in `.github/skills/daily-market-brief/tests/unit/test_aggregator.py`
- [ ] T036 [US1] Implement unit tests for social consensus anomaly detection in `.github/skills/daily-market-brief/tests/unit/test_social_consensus.py` and research reports quality scoring in `.test_research_reports.py`
- [ ] T037 [US1] Create integration test for dynamic scope adjustment using config in `.github/skills/daily-market-brief/tests/integration/test_config_change.py`

**Checkpoint**: User Story 1 fully functional - can generate complete daily report with all 5 modules using config-driven scope or gracefully handle missing sources

---

## Phase 4: User Story 2 - 逐步沉淀自动化研究流程 (Priority: P2)

**Goal**: Document and enhance automation/manual split; add operational monitoring and quality gates documentation

**Independent Test**: Read generated documentation and verify: each module documents execution phase goal, input/output schema, automation boundary, quality gate thresholds, manual review triggers, and next-phase evolution direction

### Tests for User Story 2

- [ ] T038 [P] [US2] Create unit tests for documentation generation in `.github/skills/daily-market-brief/tests/unit/test_module_docs.py`

### Implementation for User Story 2

- [ ] T039 [US2] Document module-level automation boundaries in `.github/skills/daily-market-brief/docs/module-automation.md` (FULL AUTO for all modules: US/media/commodities/social/research with quality gates; manual review only triggered by anomaly detection or data quality thresholds)
- [ ] T040 [US2] Create YAML-based phase and task mapping in `.github/skills/daily-market-brief/config/execution-phases.yaml` documenting task decomposition and dependencies
- [ ] T041 [US2] Document auto/manual split strategy and human review triggers in `.github/skills/daily-market-brief/docs/automation-roadmap.md` with future iteration targets
- [ ] T042 [US2] Add comprehensive logging of automation decision points, quality gate thresholds, and any anomaly-triggered manual review flags in each module for audit trail and continuous improvement
- [ ] T043 [US2] Add status field to each module result indicating: 'tracking list empty', 'no new items', 'X items found', 'list error' for audit trail

**Checkpoint**: User Stories 1 AND 2 complete - daily reports generated with clear automation/manual documentation and quality gates defined for continuous improvement

---

## Phase 5: User Story 3 - 深化配置驱动的范围扩展与监控 (Priority: P3)

**Goal**: Enhance configuration management and operational monitoring for production scaling

**Independent Test**: Modify tracking-lists.yaml to add/remove social media or research institutions, re-run workflow, verify report scope changes; run 20-day simulated uptime test; verify performance baseline

### Tests for User Story 3

- [ ] T044 [P] [US3] Create unit tests for config updates in `.github/skills/daily-market-brief/tests/unit/test_config_updates.py`
- [ ] T045 [P] [US3] Create performance baseline measurement test in `.github/skills/daily-market-brief/tests/integration/test_performance_baseline.py` validating SC-001 (15 min read time)
- [ ] T046 [P] [US3] Create simulated 20-day uptime test in `.github/skills/daily-market-brief/tests/integration/test_uptime_simulation.py` validating SC-002 (90% availability target)

### Implementation for User Story 3

- [ ] T047 [US3] Create documentation for maintaining tracking lists in `.github/skills/daily-market-brief/docs/tracking-lists-guide.md` with examples
- [ ] T048 [US3] Implement unit tests for scope adjustment in each module (social, research, commodities) verifying config changes propagate correctly
- [ ] T049 [US3] Add operational metrics collection: track daily run time, source availability, module success rates, and anomaly detection triggers
- [ ] T050 [US3] Document production operational runbook in `.github/skills/daily-market-brief/docs/operations-runbook.md` covering monitoring, alerting, failure recovery

**Checkpoint**: All user stories complete with operational monitoring - system ready for production deployment with clear scalability and reliability metrics

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story improvements, validation, and finalization

- [ ] T051 [P] Create comprehensive documentation updates in `.github/skills/daily-market-brief/docs/architecture.md` documenting design rationale and core decisions (D1 staged publication, D2 source layering, D3 automation-first)
- [ ] T052 [P] Create source evaluation documentation in `.github/skills/daily-market-brief/docs/source-evaluation.md` with production source recommendations (tushare, akshare, feedparser) and exploration source candidates (custom scrapers, RSSHub alternatives) documented but disabled by default (implements D2 decision)
- [ ] T053 [P] Create quickstart guide in `.github/skills/daily-market-brief/docs/quickstart.md` with one-command setup and example usage demonstrating staged publication and production-source-only defaults
- [ ] T054 [P] Create architecture documentation index in `.github/skills/daily-market-brief/docs/architecture-index.md` consolidating cross-references between module-automation.md, automation-roadmap.md, architecture.md, and quickstart.md
- [ ] T055 Code cleanup and refactoring across all modules in `.github/skills/daily-market-brief/src/` for consistency
- [ ] T056 [P] Create test coverage verification matrix in `.github/skills/daily-market-brief/tests/COVERAGE.md` linking each test task to FRs/SCs it validates
- [ ] T057 [P] Run complete test suite: `pytest .github/skills/daily-market-brief/tests/ -v` in `.github/skills/daily-market-brief/`
- [ ] T058 [P] Run cross-platform compatibility checks on macOS/Linux with platform_compat utilities
- [ ] T059 Document Windows fallback strategies in `.github/skills/daily-market-brief/docs/windows-compatibility.md`
- [ ] T060 Run local opencode validation with `./validate-daily-run.sh` and capture pass evidence
- [ ] T061 Security audit: scan `.github/skills/daily-market-brief/` for hardcoded credentials, local paths, IDE artifacts
- [ ] T062 Create `.github/skills/daily-market-brief/.gitignore` audit and verify no temporary/config files included
- [ ] T063 Verify commit hygiene: no IDE metadata, no machine-specific absolute paths, no sensitive config in repository
- [ ] T064 [P] Create final integration test running complete daily workflow end-to-end in `.github/skills/daily-market-brief/tests/integration/test_end_to_end.py`
- [ ] T065 Update `.github/copilot-instructions.md` to reference new SKILL and execution documentation
- [ ] T066 Create migration guide from Phase 0 research to Phase 1 design in `.github/skills/daily-market-brief/docs/migration-guide.md`

---

## Dependencies & Execution Strategy

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately  
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories  
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion; covers all 5 modules + staged publication + config-driven scope - MVP deliverable
- **User Story 2 (Phase 4)**: Can start after Phase 2; documents automation boundaries and quality gates  
- **User Story 3 (Phase 5)**: Can start after Phase 2; adds operational monitoring and metrics
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 - MVP deliverable with all 5 modules (US/media/social/research/commodities)
- **US2 (P2)**: Can start after Phase 2 - Extends US1 with automation documentation; independently testable
- **US3 (P3)**: Can start after Phase 2 - Extends US1/US2 with operational monitoring; independently testable

### Parallel Opportunities

- All Setup tasks marked [P] (T003-T006) can run in parallel
- All Foundational tasks marked [P] (T007-T016) can run after prerequisite utilities
- Once Phase 2 complete:
  - US1 core module tests [P] (T017-T018) and implementations [P] (T020-T026) can run in parallel
  - US1 social/research modules [P] (T024-T025) can start independently
  - US2 tests [P] (T038) and Phase 4 work can start
  - US3 tests [P] (T044-T046) and Phase 5 work can start
- All story tests marked [P] can run in parallel within each phase
- Phase 6 documentation tasks [P] (T051-T054, T057-T058, T064) can run in parallel

### Time Budget Allocation

- **Phase 1 (Setup)**: 1-2 days (with T016a PoC validation)
- **Phase 2 (Foundational)**: 2-3 days (now includes T007a config baseline)
- **Phase 3 (US1)**: 4-5 days (all 5 modules + staged publication + deduplication + conflict detection - expanded scope)
- **Phase 4 (US2)**: 1-2 days (documentation only - module implementations now in Phase 3)
- **Phase 5 (US3)**: 2-3 days (monitoring + metrics + performance/uptime testing)
- **Phase 6 (Polish)**: 2-3 days (final validation, docs consolidation)

**Total MVP (Phase 1-3): 7-10 days** (expanded from 6-9 due to full 5-module implementation in Phase 3)  
**Full feature (Phase 1-6): 12-18 days** (increased from 10-16 due to operational monitoring in Phase 5)

### Quality Gates

- All tests marked [US1]/[US2]/[US3] must pass per story
- Constitution checks (portability, setup, validation, reproducibility, hygiene) verified in Phase 6
- Local opencode validation (T060) must pass with documented evidence
- Pre-market time budget (30min aggregation, 15min readable, 1hr auto + 30min review) verified in Phase 3 integration tests

---

## MVP Scope Recommendation

**Minimum viable delivery**: Phases 1-3 (T001-T050 focusing on T020-T037)

This delivers:
- Complete daily report aggregation (US1 P1)
- All 5 core modules (US/media/social/research/commodities)
- Config-driven scope management (baseline lists in Phase 2)
- Staged publication with conflict detection and deduplication
- Graceful handling of missing sources
- Local validation framework

**Post-MVP additions**: Phases 4-5 (US2/US3 automation docs + operational monitoring) and Phase 6 (Polish) can follow in next iteration
