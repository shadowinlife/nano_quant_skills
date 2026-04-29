# Data Model: A股开盘核心新闻聚合研究 Skill

## Overview

The feature produces one daily run record, multiple module results, a configuration snapshot, and one or more aggregated reports. The data model below is intentionally file-oriented so it can be implemented with JSON and Markdown artifacts before any heavier storage choice is needed.

## Entity: DailyRunTask

Represents one end-to-end execution for a single trading date.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `run_id` | string | Yes | Unique identifier for the run | Non-empty; stable across temp/final revisions of the same run |
| `trading_date` | date string | Yes | Target trading date in `YYYY-MM-DD` format | Must be a valid date; may be a non-trading day only when explicitly overridden |
| `status` | enum | Yes | Overall workflow state | One of `queued`, `running`, `partial`, `completed`, `failed` |
| `publication_stage` | enum | Yes | Latest published stage | One of `temp`, `final` |
| `selected_modules` | string[] | Yes | Modules requested for execution | Subset of the five supported module names |
| `critical_modules` | string[] | Yes | Modules required before temp publication | Must be a subset of `selected_modules` |
| `config_version` | string | Yes | Version or checksum of the config snapshot used | Non-empty |
| `started_at` | datetime string | Yes | Execution start time | ISO 8601 |
| `completed_at` | datetime string | No | Execution end time | ISO 8601; required for `completed` and `failed` |
| `elapsed_minutes` | number | No | Total elapsed time | Greater than or equal to 0 |
| `review_status` | enum | Yes | Human review state | One of `not_required`, `pending`, `in_review`, `completed` |
| `report_ids` | string[] | No | Associated report artifacts | Empty only while run is still active |

### State Transitions

`queued -> running -> partial -> completed`  
`queued -> running -> failed`  
`running -> partial` is allowed when temp output exists but not all modules are finalized.

## Entity: TrackingConfig

Represents the versioned configuration snapshot used by a run.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `version` | string | Yes | Human-readable config version or checksum | Non-empty |
| `updated_at` | datetime string | Yes | Last config update time | ISO 8601 |
| `critical_modules` | string[] | Yes | Modules that gate temp publication | Must contain at least `us_market` and `media_mainline` for MVP |
| `time_windows` | object | Yes | Query windows per module | Keys must match module names |
| `enable_exploration_sources` | boolean | Yes | Whether exploration sources are allowed | Defaults to `false` in MVP |
| `social_accounts` | TrackingItem[] | Yes | Configured social accounts | Core list should not be empty if module enabled |
| `research_institutions` | TrackingItem[] | Yes | Configured research institutions | Core list should not be empty if module enabled |
| `commodities` | TrackingItem[] | Yes | Configured commodity topics | Core list should not be empty if module enabled |

## Entity: TrackingItem

Represents one user-maintained tracked object.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `item_id` | string | Yes | Stable identifier | Unique within its category |
| `item_type` | enum | Yes | Category of tracked item | One of `social_account`, `research_institution`, `commodity` |
| `display_name` | string | Yes | Human-readable name | Non-empty |
| `enabled` | boolean | Yes | Whether the item is active | Boolean |
| `priority` | enum | Yes | Scope tier | One of `core`, `extended` |
| `source_locator` | string | Yes | URL, feed, symbol, or provider key | Non-empty |
| `region` | string | No | Optional regional scope | Free text |
| `tags` | string[] | No | Topic tags | Optional |

## Entity: CoverageStatus

Represents the per-item execution result used for the coverage metric.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `item_id` | string | Yes | Tracked item identifier | Must exist in the config snapshot |
| `display_name` | string | Yes | Human-readable item name | Non-empty |
| `status` | enum | Yes | Coverage outcome | One of `covered`, `no_new`, `source_missing`, `list_error`, `disabled` |
| `evidence_count` | integer | Yes | Number of supporting items collected | Greater than or equal to 0 |
| `note` | string | No | Optional explanatory note | Free text |

For SC-003 accounting, only `covered`, `no_new`, and `source_missing` contribute to the success-rate numerator. `list_error` is retained as an explicit audit state, and `disabled` items are excluded from the denominator.

## Entity: ModuleResult

Represents one module's structured output for a run.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `result_id` | string | Yes | Unique result identifier | Non-empty |
| `run_id` | string | Yes | Parent run identifier | Must reference an existing `DailyRunTask` |
| `module_name` | enum | Yes | Source module | One of `us_market`, `media_mainline`, `social_consensus`, `research_reports`, `commodities` |
| `stage` | enum | Yes | Publication stage of this result | One of `temp`, `final` |
| `status` | enum | Yes | Result state | One of `confirmed`, `pending`, `missing`, `skipped`, `error`, `review_required` |
| `summary` | string | Yes | Human-readable module summary | Maximum 60 Chinese characters in MVP summary view |
| `time_window` | object | Yes | Effective analysis window | Must include a human-readable label |
| `highlights` | HighlightTopic[] | Yes | Key module topics | Maximum 5 items |
| `tracking_coverage` | CoverageStatus[] | Yes | Per-item coverage results | Required for config-driven modules |
| `evidence` | EvidenceRecord[] | Yes | Supporting references | May be empty only when status is `missing` or `skipped` |
| `anomaly_flags` | string[] | No | Triggered review flags | Required when `status = review_required` |
| `manual_review_required` | boolean | Yes | Review gate marker | Boolean |
| `generated_at` | datetime string | Yes | Result generation time | ISO 8601 |

### State Rules

- `status = skipped` requires a skip reason in `summary`.
- `manual_review_required = true` implies at least one anomaly flag.
- Config-driven modules should always emit `tracking_coverage`, even when no evidence is found.

## Entity: HighlightTopic

Represents a publishable topic candidate.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `topic_id` | string | Yes | Stable topic identifier | Non-empty |
| `title` | string | Yes | Short topic title | Non-empty; concise |
| `summary` | string | Yes | Publishable one-line summary | Maximum 60 Chinese characters |
| `priority_rank` | integer | Yes | Sort priority | Between 1 and 5 |
| `confidence` | enum | Yes | Evidence confidence | One of `high`, `medium`, `low` |
| `conflict_state` | enum | No | Cross-source consistency state | One of `aligned`, `conflicting`, `needs_review` |
| `module_origins` | string[] | Yes | Modules that surfaced the topic | At least one module |
| `evidence_refs` | string[] | Yes | Referenced evidence identifiers | May be empty only for placeholders |

## Entity: EvidenceRecord

Represents one source citation or fetched record.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `evidence_id` | string | Yes | Stable evidence identifier | Non-empty |
| `source_name` | string | Yes | Provider or feed name | Non-empty |
| `source_tier` | enum | Yes | Source maturity | One of `production`, `exploration` |
| `published_at` | datetime string | No | Publication time | ISO 8601 when available |
| `url` | string | No | Source URL | Valid URL when available |
| `headline` | string | Yes | Raw evidence title | Non-empty |
| `snippet` | string | No | Short excerpt | Free text |

## Entity: AggregatedReport

Represents the human-readable report and its structured metadata.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `report_id` | string | Yes | Unique report identifier | Non-empty |
| `run_id` | string | Yes | Parent run identifier | Must reference an existing `DailyRunTask` |
| `stage` | enum | Yes | Publication stage | One of `temp`, `final` |
| `overall_status` | enum | Yes | Report status | One of `ready`, `partial`, `review_required`, `failed` |
| `top_highlights` | HighlightTopic[] | Yes | Cross-module top highlights | Maximum 5 items |
| `sections` | ReportSection[] | Yes | Ordered report sections | Maximum 10 sections |
| `module_status` | object | Yes | Status snapshot for all five modules | Must include each module |
| `coverage_summary` | object | Yes | Aggregate coverage counts | Must include totals for `covered`, `no_new`, `source_missing`, `list_error` |
| `generated_at` | datetime string | Yes | Output time | ISO 8601 |
| `report_path` | string | Yes | Markdown artifact path | Non-empty |
| `revision_of` | string | No | Parent temp report id | Optional for final reports |

### State Rules

- `top_highlights` must not exceed 5 items.
- `sections` must not exceed 10 items.
- Each section summary shown in the report header area must stay within 60 Chinese characters.
- A temp report is publishable when all critical modules are not in `error` state.
- SC-003 attainment is calculated from `covered + no_new + source_missing`; `list_error` remains audit-only and `disabled` is excluded from the denominator.

## Entity: ReportSection

Represents one rendered section in the final Markdown report.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `title` | string | Yes | Section title | Non-empty |
| `status` | enum | Yes | Section rendering state | One of `confirmed`, `pending`, `missing`, `skipped`, `review_required` |
| `summary` | string | Yes | Section summary line | Maximum 60 Chinese characters |
| `module_refs` | string[] | Yes | Linked modules | At least one module |
| `item_refs` | string[] | No | Referenced topic ids | Optional |

## Entity: SourceAssessment

Represents the source stability record required by the specification.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `source_id` | string | Yes | Stable source identifier | Non-empty |
| `source_category` | string | Yes | Source category or provider class | Non-empty; examples: `market_api`, `rss_feed`, `research_portal`, `commodity_feed` |
| `module_name` | string | Yes | Associated module | Must match a supported module |
| `tier` | enum | Yes | Current source tier | One of `production`, `exploration` |
| `coverage_scope` | string | Yes | What the source covers | Non-empty |
| `availability_risk` | enum | Yes | Operational risk level | One of `low`, `medium`, `high` |
| `cost_notes` | string | No | Quota or cost notes | Optional |
| `fallback_source_id` | string | No | Alternate source reference | Optional |
| `review_notes` | string | No | Assessment notes | Optional |

## Relationships

- One `DailyRunTask` has many `ModuleResult` records.
- One `DailyRunTask` can publish multiple `AggregatedReport` revisions.
- One `TrackingConfig` has many `TrackingItem` records.
- Config-driven `ModuleResult` records have many `CoverageStatus` entries derived from `TrackingItem`.
- `HighlightTopic` items can appear inside both `ModuleResult` and `AggregatedReport`.
- `SourceAssessment` records describe the adapters used by module source implementations.