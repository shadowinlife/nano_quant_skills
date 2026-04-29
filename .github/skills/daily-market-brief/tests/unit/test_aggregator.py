from __future__ import annotations

import json

from models import ModuleResult
from utils.cache_manager import build_artifact_paths
from utils.config_loader import load_tracking_config
from utils.report_builder import build_aggregated_report


def test_report_builder_enforces_readability_limits() -> None:
    module_results = []
    for index in range(12):
        module_results.append(
            ModuleResult(
                run_id="demo-run",
                module="us_market" if index % 2 == 0 else "media_mainline",
                stage="final",
                status="confirmed",
                time_window={"label": "demo"},
                summary="这是一段会被报告构建器裁剪到六十个字符以内的超长摘要，用来验证摘要约束确实生效。",
                highlights=[],
                tracking_coverage=[],
                evidence=[],
            )
        )

    report = build_aggregated_report(
        run_id="demo-run",
        stage="final",
        module_results=module_results,
        report_path="tmp/demo/report.final.md",
        selected_modules=["us_market", "media_mainline"],
    )

    assert len(report.sections) <= 10
    assert all(len(section.summary) <= 60 for section in report.sections)


def test_auto_stage_keeps_temp_and_final_reports_separate(
    mock_data_dir,
    tmp_path,
    working_config,
) -> None:
    from aggregator import execute_daily_brief

    config = load_tracking_config(working_config)
    artifact_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "auto" / "report",
        cache_dir=tmp_path / "auto" / "cache",
    )

    result = execute_daily_brief(
        trading_date="2026-04-29",
        config=config,
        selected_modules=[
            "us_market",
            "media_mainline",
            "social_consensus",
            "research_reports",
            "commodities",
        ],
        stage="auto",
        strict=False,
        artifact_paths=artifact_paths,
        mock_data_dir=mock_data_dir,
    )

    assert set(result["generated_stages"]) == {"temp", "final"}

    temp_report = json.loads((artifact_paths.report_dir / "report.temp.json").read_text(encoding="utf-8"))
    final_report = json.loads((artifact_paths.report_dir / "report.final.json").read_text(encoding="utf-8"))

    assert len(temp_report["sections"]) == 2
    assert len(final_report["sections"]) == 5
    assert final_report["revision_of"] == temp_report["report_id"]