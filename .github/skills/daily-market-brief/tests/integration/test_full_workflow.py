from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from utils.cache_manager import build_artifact_paths
from utils.config_loader import load_tracking_config


REPO_ROOT = Path(__file__).resolve().parents[5]
REPORT_SCHEMA_PATH = REPO_ROOT / "specs" / "001-daily-market-brief" / "contracts" / "aggregated-report.schema.json"


def test_full_workflow_generates_temp_and_final_artifacts(
    mock_data_dir,
    tmp_path,
    working_config,
) -> None:
    from aggregator import execute_daily_brief

    config = load_tracking_config(working_config)
    artifact_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "run" / "report",
        cache_dir=tmp_path / "run" / "cache",
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

    assert result["exit_code"] == 0
    assert (artifact_paths.report_dir / "report.temp.json").exists()
    assert (artifact_paths.report_dir / "report.temp.md").exists()
    assert (artifact_paths.report_dir / "report.final.json").exists()
    assert (artifact_paths.report_dir / "report.final.md").exists()

    schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    temp_report = json.loads((artifact_paths.report_dir / "report.temp.json").read_text(encoding="utf-8"))
    final_report = json.loads((artifact_paths.report_dir / "report.final.json").read_text(encoding="utf-8"))

    assert sorted(validator.iter_errors(temp_report), key=lambda item: item.path) == []
    assert sorted(validator.iter_errors(final_report), key=lambda item: item.path) == []
    assert final_report["overall_status"] == "ready"
    assert len(final_report["top_highlights"]) <= 5
    assert len(final_report["sections"]) <= 10

    module_files = list(artifact_paths.module_results_dir.glob("*.json"))
    assert len(module_files) >= 5