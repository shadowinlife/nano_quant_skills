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
from utils.cache_manager import ArtifactPaths
from utils.cache_manager import normalize_artifact_path
from utils.cache_manager import persist_module_result
from utils.cache_manager import report_output_paths
from utils.cache_manager import write_json
from utils.cache_manager import write_markdown
from utils.report_builder import build_aggregated_report
from utils.report_builder import render_markdown


MODULE_RUNNERS = {
    "us_market": run_us_market_module,
    "media_mainline": run_media_mainline_module,
    "social_consensus": run_social_consensus_module,
    "research_reports": run_research_reports_module,
    "commodities": run_commodities_module,
}


def _ordered_selected_modules(selected_modules: list[str]) -> list[str]:
    return [module for module in MODULE_ORDER if module in selected_modules]


def _critical_ready(results_by_module: dict[str, Any], critical_modules: list[str]) -> bool:
    for module in critical_modules:
        result = results_by_module.get(module)
        if result is None or result.status != "confirmed":
            return False
    return True


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
        }

    exit_code = 3 if strict and failed_modules else 0
    return {
        "run_id": run_id,
        "exit_code": exit_code,
        "generated_stages": sorted(generated_reports),
        "report_paths": generated_reports,
        "failed_modules": failed_modules,
    }