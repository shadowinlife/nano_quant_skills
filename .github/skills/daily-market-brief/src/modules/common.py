from __future__ import annotations

from dataclasses import replace
from typing import Any

from models import CoverageStatus
from models import EvidenceRecord
from models import HighlightTopic
from models import ModuleResult
from models import TrackingItem
from models import now_iso
from utils.report_builder import truncate_summary


def build_tracking_coverage(
    tracking_items: list[TrackingItem],
    records: list[dict[str, Any]],
    source_state: str,
    note: str,
) -> list[CoverageStatus]:
    coverage: list[CoverageStatus] = []
    records_by_item: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        item_id = record.get("item_id")
        if item_id:
            records_by_item.setdefault(str(item_id), []).append(record)

    for item in tracking_items:
        if not item.enabled:
            coverage.append(
                CoverageStatus(
                    item_id=item.item_id,
                    display_name=item.display_name,
                    status="disabled",
                    evidence_count=0,
                    note="Disabled in config",
                )
            )
            continue

        matches = records_by_item.get(item.item_id, [])
        if source_state == "source_missing":
            status = "source_missing"
            explanation = note or "Source unavailable"
        elif matches:
            status = "covered"
            explanation = None
        else:
            status = "no_new"
            explanation = "No new high-confidence evidence in current window"

        coverage.append(
            CoverageStatus(
                item_id=item.item_id,
                display_name=item.display_name,
                status=status,
                evidence_count=len(matches),
                note=explanation,
            )
        )
    return coverage


def build_module_result(
    run_id: str,
    module: str,
    stage: str,
    time_window: dict[str, Any],
    source_payload: dict[str, Any],
    tracking_items: list[TrackingItem] | None = None,
    manual_review_required: bool = False,
    anomaly_flags: list[str] | None = None,
) -> ModuleResult:
    records = list(source_payload.get("records", []))
    source_state = str(source_payload.get("source_state", "ok"))
    note = str(source_payload.get("note", "")).strip()
    derived_anomaly_flags: list[str] = [
        str(flag)
        for flag in source_payload.get("anomaly_flags", [])
        if str(flag).strip()
    ]

    evidence: list[EvidenceRecord] = []
    highlights: list[HighlightTopic] = []
    for index, record in enumerate(records[:5], start=1):
        for flag in record.get("anomaly_flags", []):
            if str(flag).strip():
                derived_anomaly_flags.append(str(flag))
        if record.get("review_required"):
            derived_anomaly_flags.append(
                str(record.get("topic_id") or record.get("item_id") or f"{module}-record-{index}")
            )
        evidence_id = str(record.get("evidence_id") or f"{module}-ev-{index:03d}")
        evidence.append(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_name=str(record.get("source_name") or module),
                source_tier=str(record.get("source_tier") or "production"),
                headline=str(record.get("headline") or record.get("title") or f"{module}-{index}"),
                published_at=str(record.get("published_at") or "") or None,
                url=str(record.get("url") or "") or None,
                snippet=str(record.get("summary") or "") or None,
            )
        )
        highlights.append(
            HighlightTopic(
                topic_id=str(record.get("topic_id") or evidence_id),
                title=str(record.get("headline") or record.get("title") or f"{module}-{index}"),
                summary=truncate_summary(str(record.get("summary") or record.get("headline") or "")),
                priority_rank=min(index, 5),
                confidence=str(record.get("confidence") or "medium"),
                module_origins=[str(origin) for origin in (record.get("module_origins") or [module])],
                conflict_state=str(record.get("conflict_state")) if record.get("conflict_state") else None,
                evidence_refs=[evidence_id],
            )
        )

    deduped_anomaly_flags: list[str] = []
    for flag in [*derived_anomaly_flags, *(anomaly_flags or [])]:
        normalized_flag = str(flag).strip()
        if normalized_flag and normalized_flag not in deduped_anomaly_flags:
            deduped_anomaly_flags.append(normalized_flag)

    manual_review_required = (
        manual_review_required
        or bool(source_payload.get("manual_review_required"))
        or bool(deduped_anomaly_flags)
    )

    tracking_coverage = build_tracking_coverage(tracking_items or [], records, source_state, note)

    if manual_review_required:
        status = "review_required"
    elif source_state == "source_missing" and not records:
        status = "missing"
    elif records:
        status = "confirmed"
    elif tracking_items:
        status = "confirmed"
    else:
        status = "missing"

    if records:
        summary = truncate_summary(str(records[0].get("summary") or records[0].get("headline") or note))
    elif source_state == "source_missing":
        if tracking_items:
            checked_count = len([item for item in tracking_items if item.enabled])
            summary = truncate_summary(f"已检查 {checked_count} 个跟踪对象，当前来源不可用。")
        elif note:
            summary = truncate_summary(note)
        else:
            summary = "当前来源不可用，未获取到可发布内容。"
    elif tracking_items:
        checked_count = len([item for item in tracking_items if item.enabled])
        summary = truncate_summary(f"已检查 {checked_count} 个跟踪对象，本轮无新增高置信信息。")
    elif note:
        summary = truncate_summary(note)
    else:
        summary = "未获取到可发布内容。"

    return ModuleResult(
        run_id=run_id,
        module=module,
        stage=stage,
        status=status,
        time_window=time_window,
        summary=summary,
        highlights=highlights,
        tracking_coverage=tracking_coverage,
        evidence=evidence,
        generated_at=now_iso(),
        manual_review_required=manual_review_required,
        anomaly_flags=deduped_anomaly_flags,
        notes=[note] if note else [],
        cache_key=f"{run_id}:{module}",
    )


def clone_module_result(result: ModuleResult, stage: str) -> ModuleResult:
    return replace(result, stage=stage, generated_at=now_iso())