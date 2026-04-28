# Implementation Plan: A股开盘核心新闻聚合研究 Skill

**Branch**: `001-add-core-news-skill` | **Date**: 2026-04-28 | **Spec**: [specs/001-daily-market-brief/spec.md](spec.md)
**Input**: Feature specification from `/specs/001-daily-market-brief/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

该 Skill 的目标是为 A 股盘前投资研究提供每日核心新闻聚合与分析。通过集成多源信息（海外市场热点、主流财经媒体主线、自媒体共识、研报动态、大宗商品变化），生成结构化盘前简报。设计采用"混合架构"：轻量级 Python SKILL 作为核心编排引擎，可选集成 nano-search-mcp 与 tushare-duckdb-sync 作为数据源适配层。

### 规范一致性分析补救应用

根据 `/speckit.analyze` 结果（2026-04-28），应用了以下关键补救措施确保需求覆盖率从 82% 提升至 97%：

**Tier 1 严重问题（已解决）**:
1. **C1 - 模块阶段错配**: 将社交共识（T024）和研报（T025）模块从 Phase 4 移至 Phase 3，确保 US1 MVP 包含所有 5 个模块
2. **C2 - 配置实现时机**: 将配置加载（T007a, T041-T042 概念）移到 Phase 2 基础层，使 Phase 3-4 模块可从第一天使用动态配置
3. **C3 - 宪法第 III 门时机**: 添加 T016a（最小验证 PoC）到 Phase 1，验证设计跨平台可移植性

**Tier 2 高优先级问题（已解决）**:
1. **H1**: 添加 T045-T046（性能基准 + 正常运行时间模拟测试）验证 SC-001/SC-002
2. **H2**: 添加 T032-T033（冲突检测 + 去重复算法）到 Phase 3
3. **H3**: 在 Phase 3/4 中添加明确的阶段边界文档
4. **H4**: 添加 T028（关键模块定义列表）在 T027 前

**结果**: 总任务从 60 增至 66；FR/SC 覆盖率达到 97%；所有 5 个宪法门都通过

**核心决策**:
- **D1 (发布策略 - 选项A)**: 采用分阶段发布策略——在关键模块结果生成时允许先产出临时版报告，后续在人工复核或迟到模块完成时补充修订版，以优先满足盘前时效需求。
- **D2 (数据源探索 - 选项C)**: 采用"生产源/探索源"分层策略——首版依赖稳定接口（tushare/akshare/feedparser/RSS），定制爬虫方案仅作为候选补充路径记录在 docs/，不直接进入正式输出。
- **D3 (自动化程度 - 最大化自动化)**: 尽可能向完全自动化靠拢——除关键质检点外，所有模块的人工审核需求应最小化；社媒和研报模块应优先采用自动发现+自动验证的流程，仅在数据质量异常时触发人工介入。

## Technical Context

**Language/Version**: Python 3.11+ (aligned with nano_quant_skills infrastructure)  
**Primary Dependencies**: tushare, akshare, feedparser (RSS), requests + optional MCP client (for nano-search-mcp integration)  
**Storage**: YAML-based configuration + local Markdown/JSON intermediate results (Phase 1); SQLite/DuckDB as optional backend (Phase 2+)  
**Testing**: pytest (unit), local opencode validation (integration), bash scripts for cross-platform compatibility  
**Target Platform**: macOS, Linux, Windows (via portable Python + script wrappers)  
**Project Type**: SKILL module + optional MCP client; delivers structured daily research reports  
**Performance Goals**: Daily aggregation completes within 30 minutes from data collection to report generation; reports readable within 15 minutes by researcher  
**Constraints**: Pre-market delivery (before 09:30 CN time); graceful degradation when individual sources unavailable; zero hardcoded local paths or credentials in commits  
**Scale/Scope**: Initial coverage: 5-8 core US indices + 10-15 CN media sources + 20-30 social media accounts + 5-10 key research institutions + 10-15 commodity tracking items; expandable via config

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Portability gate** ✓ PASS: Core SKILL uses cross-platform Python; all subprocess calls wrapped in portable shell abstractions; fallback to graceful mode-down when platform-specific tools unavailable (e.g., cron → manual trigger on Windows).
- **Setup gate** ✓ PASS: Lightweight setup requires only `pip install tushare akshare feedparser` + conda env already present (legonanobot); config YAML templates provided with sensible defaults; no external service startup required for Phase 1.
- **Opencode validation gate** ✓ PASS: Local validation via `pytest tests/` + documented `./validate-daily-run.sh` script that runs one complete workflow locally and outputs verification checklist before commit.
- **Reproducibility gate** ✓ PASS: Each module specifies input sources, output schema, error handling, and retry logic; deterministic invocation via CLI or SKILL entry point with explicit config paths.
- **Hygiene and privacy gate** ✓ PASS: Configuration templates use placeholder credentials; validation script scans commits for hardcoded paths/secrets before pushing; temp files written to `.gitignore`-tracked `./tmp/` and `.cache/` dirs.

## Project Structure

### Documentation (this feature)

```text
specs/001-daily-market-brief/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── config-schema.md # YAML configuration contract for tracking lists
│   ├── module-output.md # Intermediate result schema for each module
│   └── report-format.md # Final aggregated report structure
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
.github/skills/daily-market-brief/
├── SKILL.md             # Skill definition for Copilot integration
├── README.md            # Setup & usage guide
├── config/
│   ├── tracking-lists.yaml     # User-maintained tracking config (social media, research institutions, commodities)
│   └── config.example.yaml     # Template with defaults
├── src/
│   ├── main.py          # SKILL entry point & CLI
│   ├── aggregator.py    # Main orchestration engine
│   ├── modules/
│   │   ├── us_market.py        # Module 1: US market hotspots (FULL AUTO)
│   │   ├── media_mainline.py   # Module 2: CN media mainline extraction (FULL AUTO)
│   │   ├── social_consensus.py # Module 3: Social media consensus (SEMI-AUTO: auto scrape + human review flag)
│   │   ├── research_reports.py # Module 4: Research report tracking (SEMI-AUTO: discovery + manual validation)
│   │   └── commodities.py      # Module 5: Commodity tracking (FULL AUTO)
│   ├── sources/
│   │   ├── us_market_feed.py   # US market hotspots (tushare + news API)
│   │   ├── media_feed.py       # CN media RSS aggregation
│   │   ├── social_feed.py      # Social media scraping (Weibo, Snowball, public APIs)
│   │   ├── research_feed.py    # Research report discovery APIs
│   │   └── commodity_feed.py   # Commodity price + news feeds
│   └── utils/
│       ├── config_loader.py    # YAML config parsing
│       ├── report_builder.py   # Report aggregation & markdown export
│       ├── cache_manager.py    # Local JSON cache for intermediate results
│       ├── platform_compat.py  # Cross-platform path/subprocess handling
│       └── logger.py           # Structured logging
├── tests/
│   ├── unit/
│   │   ├── test_modules.py
│   │   ├── test_sources.py
│   │   ├── test_config.py
│   │   └── test_report_builder.py
│   └── integration/
│       └── test_full_workflow.py
│   └── fixtures/
│       └── mock_data/
├── docs/
│   ├── architecture.md         # Design rationale
│   ├── source-evaluation.md    # Candidates: tushare, akshare, RSSHub, custom scrapers
│   ├── data-model.md           # Generated in Phase 1
│   └── contracts/              # Generated in Phase 1
├── validate-daily-run.sh       # Local opencode validation script
├── requirements.txt            # Python dependencies (tushare, akshare, feedparser, requests, ...)
└── .gitignore                  # Exclude tmp/, .cache/, *.log, credentials
```

## Phase 0: Research & Source Exploration

### Unknowns to Resolve

1. **US Market Hotspot Data Source**  
   Research: Compare tushare vs. direct Yahoo/TradingView APIs for intraday US market sentiment & hotspots; identify most stable + accessible approach.

2. **CN Media Mainline Information**  
   Research: Map available RSS feeds from CNBC, ABC, 第一财经, 新浪财经, 雪球; evaluate coverage & latency; identify fallback sources if primary unavailable.

3. **Social Media Consensus Extraction**  
   Research: Explore Weibo API, Snowball (雪球) public APIs, WeChat subscription aggregators; define scope for "past 5 trading days" window; identify data freshness constraints.

4. **Research Report Discovery**  
   Research: Identify available APIs for domestic research institutions (国信、东吴、中信等) & overseas firms (Goldman Sachs, Morgan Stanley); evaluate accessibility & update frequency.

5. **Commodity Price + Regional News**  
   Research: Identify stable commodity price feeds (tushare, akshare, Bloomberg); map news sources for key production regions; define alert thresholds.

6. **Data Source Stability & Fallback**  
   Research: For each source type, document: API rate limits, SLA expectations, known failure modes, alternative providers, cost/license constraints.

### Output Artifacts

- **research.md**: Decision matrix for each source type with recommendations
- Updated `docs/source-evaluation.md` with rationale & fallback strategies
- Identified quick-start data sources for Phase 1 MVP

## Phase 1: Design & Interface Contracts

### Data Model (to be generated)

Key entities:
- **DailyRunTask**: Execution metadata (date, modules enabled, status)
- **ModuleResult**: Structured output from each analysis module (summary, sources, confidence, human-review-needed flag)
- **TrackingConfig**: User-maintained lists (social media, research institutions, commodities)
- **AggregatedReport**: Final output with section-level prioritization & gap markers

### Interface Contracts (to be generated)

1. **Configuration Schema**: YAML structure for tracking lists, source endpoints, time windows
2. **Module Output Schema**: JSON/Markdown intermediate result format (title, summary, sources, flags)
3. **Report Format**: Final markdown report structure with sections, priority indicators, evidence linkage

### Quickstart Guide (to be generated)

- One-command setup (conda environment + pip install)
- Example: `python .github/skills/daily-market-brief/src/main.py --date 2026-04-28 --config ./config/tracking-lists.yaml`
- Expected output location & format

## Phase 1 Post-Design: Agent Context Update

After Phase 1 design completion, update `.github/copilot-instructions.md` to reference this plan file path.

## Constitution Re-Check Post-Phase 1

Confirm all five gates still passing with concrete design artifacts in place.
