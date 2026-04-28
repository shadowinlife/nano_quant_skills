# Planning Decisions Record

**Date**: 2026-04-28  
**Feature**: A股开盘核心新闻聚合研究 Skill (001-daily-market-brief)  
**Status**: Finalized

---

## Decision 1: Report Publication Strategy

**Decision**: D1 - Staged Publication (Option A)

**Description**: The system adopts a staged publication strategy where critical modules generate a temporary report that can be published immediately to meet pre-market time constraints. Later-arriving modules or human review results can be folded into a revised report without blocking initial delivery.

**Rationale**:
- A 股 开盘前的时效性要求（09:30）是硬约束
- 部分数据源存在延迟风险，不应阻塞整份报告的交付
- 允许"临时版→修订版"的流程可以最大化盘前时效性

**Implementation**:
- Aggregator implements two-stage workflow: critical module completion triggers temp report export, human review/late-arriving modules update revision
- Temp and revision reports marked with timestamps and completeness flags
- Configuration defines which modules are "critical" for initial publication

**Impact on Tasks**:
- T025: Staged publication strategy implementation in aggregator
- T032: Data source layering respects production vs. exploration tiers to optimize for critical-module-first workflow

---

## Decision 2: Data Source Exploration Boundary

**Decision**: D2 - Layered Source Strategy (Option C)

**Description**: Production sources (tushare, akshare, feedparser, standard RSS feeds) form the default operational tier. Exploration sources (custom scrapers, API alternatives, experimental data providers) are documented in `docs/source-evaluation.md` and made available as disabled-by-default options for future enablement.

**Rationale**:
- Phase 1 MVP 优先稳定性，自定义爬虫方案带来维护成本和 IP 限制风险
- 将探索性来源记录下来便于后续迭代和 A/B 测试
- 生产源和探索源分离降低初期风险，同时保留扩展空间

**Implementation**:
- Requirements.txt specifies only production dependencies (tushare, akshare, feedparser, requests)
- docs/source-evaluation.md documents all candidate sources with assessment matrix (accessibility, latency, cost, fallback options)
- Source modules include feature flags for exploration sources; disabled by default
- Configuration schema supports future source tier elevation as confidence grows

**Impact on Tasks**:
- T023: Production source implementations only in initial phase
- T048: Source evaluation doc defines both tiers and maturity assessment criteria
- T049: Quickstart defaults to production sources only

---

## Decision 3: Automation Maximization

**Decision**: D3 - Automation-First Approach

**Description**: All five analysis modules operate with full automation as the default path. Manual intervention is triggered only by explicitly detected anomalies or quality gate violations, not as a design default. Even for US2/P2 scope (social consensus, research reports), automation should be maximized with quality-driven manual review gates rather than planned manual steps.

**Rationale**:
- 盘前时效是硬约束，人工介入必然延迟整份报告
- 可以通过质量门槛和异常检测来触发人工复核，而不是预设人工介入步骤
- 逐步建立可信度后，人工复核可以进一步减少

**Implementation**:
- Social consensus module (US2): Full auto scraping + consensus detection; manual review triggered by consensus threshold violations or source count anomalies
- Research reports module (US2): Full auto discovery + relevance scoring + publication date validation; manual review triggered by score anomalies or duplicate detection failures
- All modules include anomaly detection rules and quality thresholds in logging
- Audit trail captures why manual review was triggered (if at all)

**Impact on Tasks**:
- T030, T031: Modules marked as "FULL AUTO with quality gates" instead of "SEMI-AUTO"
- T036: Comprehensive logging of automation decision points and threshold triggers
- T037: Unit tests validate automation thresholds and anomaly detection logic
- T033: Documentation emphasizes quality-gate-driven manual review over planned manual steps

---

## Cross-Decision Consistency

| Aspect | D1 Impact | D2 Impact | D3 Impact |
|--------|-----------|-----------|-----------|
| Time-to-market | Staged pub reduces latency | Production sources prioritized | Full auto minimizes delays |
| Risk profile | Lower (temp + revision) | Lower (stable sources) | Manageable (quality gates) |
| Maintenance cost | Moderate (dual outputs) | Low (no custom scrapers) | Low (anomaly detection replaces manual review) |
| Expandability | High (revision cycle enabled) | High (exploration tier ready) | High (thresholds tunable) |

---

## Future Iterations

### Phase 2 Evolution Path

If Phase 1 MVP achieves >95% uptime with <5% anomaly-triggered manual reviews:
- Consider promoting selected exploration sources to production tier
- Reduce anomaly thresholds as confidence in auto-detection grows
- Evaluate merging temp + revision publication into single optimized flow

### Data Source Graduation Criteria

Exploration source → Production source when:
1. 95%+ availability SLA demonstrated over 20 trading days
2. Latency <5% above production source median
3. <2% false-positive rate in anomaly detection
4. Integration cost (maintenance hours) within operational budget

---

## Decision Sign-Off

- **Planner**: Auto-decided based on specification and constraints
- **Validation**: All three decisions align with Constitution gates and pre-market time requirements
- **Date**: 2026-04-28
