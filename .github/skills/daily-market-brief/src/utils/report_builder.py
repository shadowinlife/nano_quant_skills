from __future__ import annotations

from collections import Counter

from models import AggregatedReport
from models import MODULE_LABELS
from models import MODULE_ORDER
from models import ModuleResult
from models import ReportSection
from models import now_iso


MAX_HIGHLIGHTS = 5
MAX_SECTIONS = 10
MAX_SUMMARY_CHARS = 60

STATUS_MARKERS = {
    "confirmed": "[confirmed]",
    "pending": "[pending]",
    "missing": "[missing]",
    "skipped": "[skipped]",
    "review_required": "[review]",
    "error": "[error]",
    "disabled": "[disabled]",
}


def truncate_summary(text: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return f"{clean[: max_chars - 1]}…"


def build_coverage_summary(module_results: list[ModuleResult]) -> dict[str, int]:
    counter: Counter[str] = Counter({
        "covered": 0,
        "no_new": 0,
        "source_missing": 0,
        "list_error": 0,
        "disabled": 0,
    })
    for result in module_results:
        for entry in result.tracking_coverage:
            counter[entry.status] += 1
    return dict(counter)


def _pick_top_highlights(module_results: list[ModuleResult]) -> list:
    ranked: dict[str, object] = {}
    for result in module_results:
        for highlight in result.highlights:
            key = highlight.topic_id or highlight.title
            existing = ranked.get(key)
            if existing is None or highlight.priority_rank < existing.priority_rank:
                ranked[key] = highlight
    ordered = sorted(ranked.values(), key=lambda item: (item.priority_rank, item.title))
    return ordered[:MAX_HIGHLIGHTS]


def build_sections(module_results: list[ModuleResult]) -> list[ReportSection]:
    sections: list[ReportSection] = []
    for result in module_results:
        sections.append(
            ReportSection(
                title=MODULE_LABELS.get(result.module, result.module),
                status=result.status,
                summary=truncate_summary(result.summary),
                module_refs=[result.module],
                item_refs=[item.topic_id for item in result.highlights],
                evidence_refs=[item.evidence_id for item in result.evidence],
            )
        )
    return sections[:MAX_SECTIONS]


def determine_overall_status(module_results: list[ModuleResult], selected_modules: list[str]) -> str:
    if not module_results:
        return "failed"
    result_map = {result.module: result.status for result in module_results}
    statuses = [result_map.get(module, "missing") for module in selected_modules]
    if any(status == "review_required" for status in statuses):
        return "review_required"
    if any(status in {"missing", "pending", "skipped", "error"} for status in statuses):
        return "partial"
    return "ready"


def build_aggregated_report(
    run_id: str,
    stage: str,
    module_results: list[ModuleResult],
    report_path: str,
    selected_modules: list[str] | None = None,
    revision_of: str | None = None,
) -> AggregatedReport:
    selected = selected_modules or MODULE_ORDER
    module_status = {module: "disabled" for module in MODULE_ORDER}
    for module in selected:
        module_status[module] = "missing"
    for result in module_results:
        module_status[result.module] = result.status

    return AggregatedReport(
        report_id=f"{run_id}:{stage}",
        run_id=run_id,
        stage=stage,
        overall_status=determine_overall_status(module_results, selected),
        generated_at=now_iso(),
        top_highlights=_pick_top_highlights(module_results),
        sections=build_sections(module_results),
        module_status=module_status,
        coverage_summary=build_coverage_summary(module_results),
        report_path=report_path,
        revision_of=revision_of,
    )


def render_markdown(report: AggregatedReport, module_results: list[ModuleResult]) -> str:
    lines = [
        "# A股盘前核心新闻简报",
        "",
        f"- run_id: {report.run_id}",
        f"- stage: {report.stage}",
        f"- overall_status: {report.overall_status}",
        f"- generated_at: {report.generated_at}",
        "",
        "## 顶部高光",
        "",
    ]

    if report.top_highlights:
        for highlight in report.top_highlights:
            lines.append(
                f"- {highlight.title}: {truncate_summary(highlight.summary)}"
            )
    else:
        lines.append("- 暂无高光主题")

    lines.extend(["", "## 模块状态", ""])
    for module in MODULE_ORDER:
        marker = STATUS_MARKERS.get(report.module_status.get(module, "missing"), "[unknown]")
        lines.append(f"- {marker} {MODULE_LABELS.get(module, module)}")

    lines.extend(["", "## 正文板块", ""])
    for section in report.sections:
        marker = STATUS_MARKERS.get(section.status, "[unknown]")
        lines.append(f"### {marker} {section.title}")
        lines.append(section.summary)
        module_result = next((item for item in module_results if item.module in section.module_refs), None)
        # FR-029: show skip_reason for skipped sections
        if module_result and module_result.status == "skipped" and module_result.skip_reason:
            lines.append(f"ℹ️ 跳过原因：{module_result.skip_reason}")
        if module_result and module_result.semantic_drift:
            drifts = ", ".join(module_result.semantic_drift.get("drift_categories", []))
            lines.append(f"⚠️ 语义漂移检测：{drifts}")
        if module_result:
            lagging = [
                ev for ev in module_result.evidence
                if getattr(ev, "previous_session_gap_days", None) is not None
            ]
            if lagging:
                lines.append(f"⚠️ 行情滞后：{len(lagging)} 条行情数据与目标日期差距超过 5 个自然日")
        if module_result and module_result.highlights:
            for highlight in module_result.highlights[:MAX_HIGHLIGHTS]:
                lines.append(f"- {highlight.title}: {truncate_summary(highlight.summary)}")
        else:
            lines.append("- 本板块暂无新增高置信信息")
        lines.append("")

    lines.extend(["## 覆盖统计", ""])
    for key, value in report.coverage_summary.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines).strip() + "\n"