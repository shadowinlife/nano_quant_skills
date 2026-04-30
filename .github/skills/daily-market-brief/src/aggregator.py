from __future__ import annotations

from pathlib import Path
from typing import Any

from models import MODULE_ORDER
from models import TrackingConfig
from modules import run_commodities_module
from modules import run_media_mainline_module
from modules import run_research_reports_module
from modules import run_social_consensus_module
from modules import run_us_market_module
from modules.common import clone_module_result
from run_summary import write_run_summary
from utils.cache_manager import ArtifactPaths
from utils.cache_manager import normalize_artifact_path
from utils.cache_manager import persist_module_result
from utils.cache_manager import report_output_paths
from utils.cache_manager import write_json
from utils.cache_manager import write_markdown
from utils.report_builder import build_aggregated_report
from utils.report_builder import render_markdown
from utils.source_independence import check_source_independence


MODULE_RUNNERS = {
    "us_market": run_us_market_module,
    "media_mainline": run_media_mainline_module,
    "social_consensus": run_social_consensus_module,
    "research_reports": run_research_reports_module,
    "commodities": run_commodities_module,
}

# Static source metadata: declared_sources and declared_semantic_tag per module.
_MODULE_DECLARED_SOURCES: dict[str, list[str]] = {
    "us_market": ["us-market-rss"],
    "media_mainline": ["media-mainline-rss"],
    "social_consensus": ["social-tracking-feeds"],
    "research_reports": ["research-tracking-feeds"],
    "commodities": ["commodity-symbol-feed"],
}

_MODULE_DECLARED_SEMANTIC_TAGS: dict[str, dict[str, Any]] = {
    "us_market": {"language": "en", "region": "us", "media_type": "newswire"},
    "media_mainline": {"language": "zh", "region": "cn", "media_type": "newswire"},
    "social_consensus": {"language": "zh", "region": "cn", "media_type": "social"},
    "research_reports": {"language": "zh", "region": "cn", "media_type": "research_report"},
    "commodities": {"language": "zh", "region": "global", "media_type": "commodity_data"},
}


def _ordered_selected_modules(selected_modules: list[str]) -> list[str]:
    return [module for module in MODULE_ORDER if module in selected_modules]


def _critical_ready(results_by_module: dict[str, Any], critical_modules: list[str]) -> bool:
    for module in critical_modules:
        result = results_by_module.get(module)
        if result is None or result.status != "confirmed":
            return False
    return True


def _build_attempted_source_entry(source_id: str, module_result: Any) -> dict[str, Any]:
    """Build a minimal attemptedSource entry for the run-summary from a module result."""
    protocol = "rss" if "rss" in source_id else ("sdk_api" if "symbol" in source_id else "http_scrape")
    fail_class = None
    if module_result.status in {"missing", "error"}:
        fail_class = "parse_empty"
    return {
        "url": source_id,
        "protocol": protocol,
        "http_status": None,
        "records": len(module_result.evidence),
        "fail_class": fail_class,
    }


def _build_run_summary_module_entries(
    ordered_modules: list[str],
    results_by_module: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for module in ordered_modules:
        result = results_by_module.get(module)
        if result is None:
            continue
        declared_sources = _MODULE_DECLARED_SOURCES.get(module, [])
        declared_semantic_tag = _MODULE_DECLARED_SEMANTIC_TAGS.get(module, {})

        # Prefer result.attempted_source_ids if populated, else fall back to declared sources
        if result.attempted_source_ids:
            attempted = [
                {"url": src_id, "protocol": "http_scrape", "http_status": None, "records": 0, "fail_class": None}
                for src_id in result.attempted_source_ids
            ]
        else:
            attempted = [_build_attempted_source_entry(src_id, result) for src_id in declared_sources]

        entry: dict[str, Any] = {
            "module": module,
            "declared_semantic_tag": declared_semantic_tag,
            "declared_sources": declared_sources,
            "attempted_sources": attempted,
            "final_status": result.status,
        }
        if result.semantic_drift is not None:
            entry["semantic_drift"] = result.semantic_drift
        entries.append(entry)
    return entries


def _persist_report(stage: str, report, module_results, artifact_paths: ArtifactPaths) -> dict[str, str]:
    report_json_path, report_md_path = report_output_paths(artifact_paths, stage)
    write_json(report_json_path, report.to_dict())
    write_markdown(report_md_path, render_markdown(report, module_results))
    return {
        "json": str(report_json_path),
        "markdown": str(report_md_path),
    }


def execute_daily_brief(
    trading_date: str,
    config: TrackingConfig,
    selected_modules: list[str],
    stage: str,
    strict: bool,
    artifact_paths: ArtifactPaths,
    mock_data_dir: str | Path | None = None,
    preflight_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return _execute_daily_brief_impl(
            trading_date=trading_date,
            config=config,
            selected_modules=selected_modules,
            stage=stage,
            strict=strict,
            artifact_paths=artifact_paths,
            mock_data_dir=mock_data_dir,
            preflight_result=preflight_result,
        )
    except Exception as exc:
        return {
            "run_id": f"{trading_date}:error",
            "exit_code": 5,
            "message": f"Uncaught internal error: {type(exc).__name__}: {exc}",
        }


def _execute_daily_brief_impl(
    trading_date: str,
    config: TrackingConfig,
    selected_modules: list[str],
    stage: str,
    strict: bool,
    artifact_paths: ArtifactPaths,
    mock_data_dir: str | Path | None = None,
    preflight_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ordered_modules = _ordered_selected_modules(selected_modules)
    run_id = f"{trading_date}:{config.snapshot_version}"
    critical_modules = [module for module in config.critical_modules if module in ordered_modules]
    if stage in {"temp", "auto"} and set(critical_modules) != set(config.critical_modules):
        return {
            "run_id": run_id,
            "exit_code": 3,
            "message": "Selected modules do not include all critical modules required for temp publication.",
        }

    results_by_module: dict[str, Any] = {}
    final_results: list[Any] = []
    generated_reports: dict[str, dict[str, str]] = {}
    revision_of: str | None = None

    for module in ordered_modules:
        runner = MODULE_RUNNERS[module]
        base_result = runner(
            run_id=run_id,
            trading_date=trading_date,
            config=config,
            stage="final",
            mock_data_dir=mock_data_dir,
        )
        results_by_module[module] = base_result
        final_results.append(base_result)

        if stage in {"temp", "auto"} and "temp" not in generated_reports and _critical_ready(results_by_module, critical_modules):
            temp_results = [clone_module_result(results_by_module[name], "temp") for name in critical_modules]
            for item in temp_results:
                persist_module_result(item.to_dict(), artifact_paths)
            temp_json_path, temp_md_path = report_output_paths(artifact_paths, "temp")
            temp_report = build_aggregated_report(
                run_id=run_id,
                stage="temp",
                module_results=temp_results,
                report_path=normalize_artifact_path(temp_md_path),
                selected_modules=critical_modules,
            )
            generated_reports["temp"] = _persist_report("temp", temp_report, temp_results, artifact_paths)
            revision_of = temp_report.report_id
            if stage == "temp":
                return {
                    "run_id": run_id,
                    "exit_code": 0,
                    "generated_stages": ["temp"],
                    "report_paths": generated_reports,
                }

    if stage in {"temp", "auto"} and "temp" not in generated_reports:
        return {
            "run_id": run_id,
            "exit_code": 3,
            "message": "Critical modules did not reach a publishable state.",
        }

    final_stage_results = [clone_module_result(item, "final") for item in final_results]
    for item in final_stage_results:
        persist_module_result(item.to_dict(), artifact_paths)

    final_json_path, final_md_path = report_output_paths(artifact_paths, "final")
    final_report = build_aggregated_report(
        run_id=run_id,
        stage="final",
        module_results=final_stage_results,
        report_path=normalize_artifact_path(final_md_path),
        selected_modules=ordered_modules,
        revision_of=revision_of,
    )
    generated_reports["final"] = _persist_report("final", final_report, final_stage_results, artifact_paths)

    # FR-028: coverage consistency assertion
    from utils.report_builder import build_coverage_summary as _bcs
    _expected_coverage_keys = set(_bcs([]).keys())  # canonical key set from empty run
    _actual_coverage_keys = set(final_report.coverage_summary.keys())
    _unexpected = _actual_coverage_keys - _expected_coverage_keys
    _missing = _expected_coverage_keys - _actual_coverage_keys
    if _unexpected or _missing:
        import logging as _log
        _logger2 = _log.getLogger("daily-market-brief.aggregator")
        if _unexpected:
            _logger2.warning("coverage_consistency: unexpected keys in coverage_summary: %s", sorted(_unexpected))
        if _missing:
            _logger2.warning("coverage_consistency: missing expected keys in coverage_summary: %s", sorted(_missing))

    # Write run-summary.json
    pf = preflight_result or {"ok": True, "missing": []}
    module_entries = _build_run_summary_module_entries(ordered_modules, results_by_module)

    # FR-026: source independence check
    source_violations = check_source_independence(module_entries)
    if source_violations:
        import logging
        _logger = logging.getLogger("daily-market-brief.aggregator")
        for violation in source_violations:
            _logger.warning("source_independence: %s", violation)

    summary_path = write_run_summary(
        run_id=run_id,
        trade_date=trading_date,
        preflight_ok=bool(pf.get("ok", True)),
        preflight_missing=list(pf.get("missing", [])),
        module_entries=module_entries,
        output_dir=artifact_paths.report_dir,
        coverage_summary=final_report.coverage_summary,
    )
    final_report.run_summary_path = str(summary_path)

    failed_modules = [
        result.module
        for result in final_stage_results
        if result.status in {"missing", "error", "review_required"}
    ]
    if any(module in config.critical_modules for module in failed_modules):
        return {
            "run_id": run_id,
            "exit_code": 3,
            "generated_stages": sorted(generated_reports),
            "report_paths": generated_reports,
            "failed_modules": failed_modules,
            "run_summary_path": str(summary_path),
        }

    exit_code = 3 if strict and failed_modules else 0
    return {
        "run_id": run_id,
        "exit_code": exit_code,
        "generated_stages": sorted(generated_reports),
        "report_paths": generated_reports,
        "failed_modules": failed_modules,
        "run_summary_path": str(summary_path),
    }