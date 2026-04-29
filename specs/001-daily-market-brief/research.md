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