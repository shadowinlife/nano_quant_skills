from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any

MODULE_ORDER = [
    "us_market",
    "media_mainline",
    "social_consensus",
    "research_reports",
    "commodities",
]

MODULE_LABELS = {
    "us_market": "美股热点",
    "media_mainline": "主流财经媒体",
    "social_consensus": "自媒体共识",
    "research_reports": "研报动态",
    "commodities": "大宗商品",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class TrackingItem:
    item_id: str
    item_type: str
    display_name: str
    enabled: bool
    priority: str
    source_locator: str
    region: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    disabled_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "display_name": self.display_name,
            "enabled": self.enabled,
            "priority": self.priority,
            "source_locator": self.source_locator,
            "tags": self.tags,
        }
        if self.region:
            data["region"] = self.region
        data.update(self.metadata)
        return data


@dataclass(slots=True)
class CoverageStatus:
    item_id: str
    display_name: str
    status: str
    evidence_count: int
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "item_id": self.item_id,
            "display_name": self.display_name,
            "status": self.status,
            "evidence_count": self.evidence_count,
        }
        if self.note:
            data["note"] = self.note
        return data


@dataclass(slots=True)
class HighlightTopic:
    topic_id: str
    title: str
    summary: str
    priority_rank: int
    confidence: str
    module_origins: list[str] = field(default_factory=list)
    conflict_state: str | None = None
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "topic_id": self.topic_id,
            "title": self.title,
            "summary": self.summary,
            "priority_rank": self.priority_rank,
            "confidence": self.confidence,
        }
        if self.module_origins:
            data["module_origins"] = self.module_origins
        if self.conflict_state:
            data["conflict_state"] = self.conflict_state
        if self.evidence_refs:
            data["evidence_refs"] = self.evidence_refs
        return data


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    source_name: str
    source_tier: str
    headline: str
    published_at: str | None = None
    url: str | None = None
    snippet: str | None = None
    trade_date: str | None = None
    previous_session_gap_days: int | None = None
    semantic_tag: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "evidence_id": self.evidence_id,
            "source_name": self.source_name,
            "source_tier": self.source_tier,
            "headline": self.headline,
        }
        if self.published_at:
            data["published_at"] = self.published_at
        if self.url:
            data["url"] = self.url
        if self.snippet:
            data["snippet"] = self.snippet
        if self.trade_date:
            data["trade_date"] = self.trade_date
        if self.previous_session_gap_days is not None:
            data["previous_session_gap_days"] = self.previous_session_gap_days
        if self.semantic_tag:
            data["semantic_tag"] = self.semantic_tag
        return data


@dataclass(slots=True)
class ModuleResult:
    run_id: str
    module: str
    stage: str
    status: str
    time_window: dict[str, Any]
    summary: str
    highlights: list[HighlightTopic] = field(default_factory=list)
    tracking_coverage: list[CoverageStatus] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    generated_at: str = field(default_factory=now_iso)
    manual_review_required: bool = False
    anomaly_flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    cache_key: str | None = None
    semantic_drift: dict[str, Any] | None = None
    attempted_source_ids: list[str] = field(default_factory=list)
    skip_reason: str | None = None

    @property
    def result_id(self) -> str:
        return f"{self.run_id}:{self.module}:{self.stage}"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "run_id": self.run_id,
            "module": self.module,
            "stage": self.stage,
            "status": self.status,
            "time_window": self.time_window,
            "summary": self.summary,
            "highlights": [item.to_dict() for item in self.highlights],
            "tracking_coverage": [item.to_dict() for item in self.tracking_coverage],
            "evidence": [item.to_dict() for item in self.evidence],
            "generated_at": self.generated_at,
            "manual_review_required": self.manual_review_required,
        }
        if self.anomaly_flags:
            data["anomaly_flags"] = self.anomaly_flags
        if self.notes:
            data["notes"] = self.notes
        if self.cache_key:
            data["cache_key"] = self.cache_key
        if self.semantic_drift is not None:
            data["semantic_drift"] = self.semantic_drift
        if self.attempted_source_ids:
            data["attempted_source_ids"] = self.attempted_source_ids
        if self.skip_reason is not None:
            data["skip_reason"] = self.skip_reason
        return data


@dataclass(slots=True)
class ReportSection:
    title: str
    status: str
    summary: str
    module_refs: list[str]
    item_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "module_refs": self.module_refs,
        }
        if self.item_refs:
            data["item_refs"] = self.item_refs
        if self.evidence_refs:
            data["evidence_refs"] = self.evidence_refs
        return data


@dataclass(slots=True)
class AggregatedReport:
    report_id: str
    run_id: str
    stage: str
    overall_status: str
    generated_at: str
    top_highlights: list[HighlightTopic]
    sections: list[ReportSection]
    module_status: dict[str, str]
    coverage_summary: dict[str, int]
    report_path: str
    revision_of: str | None = None
    run_summary_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "stage": self.stage,
            "overall_status": self.overall_status,
            "generated_at": self.generated_at,
            "top_highlights": [item.to_dict() for item in self.top_highlights],
            "sections": [item.to_dict() for item in self.sections],
            "module_status": self.module_status,
            "coverage_summary": self.coverage_summary,
            "report_path": self.report_path,
        }
        if self.revision_of:
            data["revision_of"] = self.revision_of
        if self.run_summary_path:
            data["run_summary_path"] = self.run_summary_path
        return data


@dataclass(slots=True)
class DailyRunTask:
    run_id: str
    trading_date: str
    status: str
    publication_stage: str
    selected_modules: list[str]
    critical_modules: list[str]
    config_version: str
    started_at: str = field(default_factory=now_iso)
    completed_at: str | None = None
    elapsed_minutes: float | None = None
    review_status: str = "not_required"
    report_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "run_id": self.run_id,
            "trading_date": self.trading_date,
            "status": self.status,
            "publication_stage": self.publication_stage,
            "selected_modules": self.selected_modules,
            "critical_modules": self.critical_modules,
            "config_version": self.config_version,
            "started_at": self.started_at,
            "review_status": self.review_status,
            "report_ids": self.report_ids,
        }
        if self.completed_at:
            data["completed_at"] = self.completed_at
        if self.elapsed_minutes is not None:
            data["elapsed_minutes"] = self.elapsed_minutes
        return data


@dataclass(slots=True)
class TrackingConfig:
    version: str
    updated_at: str
    critical_modules: list[str]
    time_windows: dict[str, dict[str, Any]]
    enable_exploration_sources: bool
    social_accounts: list[TrackingItem]
    research_institutions: list[TrackingItem]
    commodities: list[TrackingItem]
    module_enabled: dict[str, bool] = field(default_factory=dict)
    source_tiers: dict[str, str] = field(default_factory=dict)
    tracking_lists_path: str = ""
    snapshot_version: str = ""
    artifact_defaults: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "critical_modules": self.critical_modules,
            "time_windows": self.time_windows,
            "enable_exploration_sources": self.enable_exploration_sources,
            "social_accounts": [item.to_dict() for item in self.social_accounts],
            "research_institutions": [item.to_dict() for item in self.research_institutions],
            "commodities": [item.to_dict() for item in self.commodities],
            "module_enabled": self.module_enabled,
            "source_tiers": self.source_tiers,
            "tracking_lists_path": self.tracking_lists_path,
            "snapshot_version": self.snapshot_version,
            "artifact_defaults": self.artifact_defaults,
        }