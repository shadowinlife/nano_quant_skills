from __future__ import annotations

import json
from pathlib import Path

import yaml

from utils.cache_manager import build_artifact_paths
from utils.config_loader import build_config_snapshot
from utils.config_loader import diff_config_snapshots
from utils.config_loader import load_tracking_config


def test_tracking_list_updates_change_scope_without_breaking_report_shape(
    mock_data_dir,
    tmp_path,
    working_config,
) -> None:
    from aggregator import execute_daily_brief

    tracking_file = Path(working_config).with_name("tracking-lists.yaml")
    original_config = load_tracking_config(working_config)

    baseline_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "baseline" / "report",
        cache_dir=tmp_path / "baseline" / "cache",
    )
    baseline_result = execute_daily_brief(
        trading_date="2026-04-29",
        config=original_config,
        selected_modules=["social_consensus", "research_reports", "commodities"],
        stage="final",
        strict=False,
        artifact_paths=baseline_paths,
        mock_data_dir=mock_data_dir,
    )
    assert baseline_result["exit_code"] == 0
    baseline_report = json.loads((baseline_paths.report_dir / "report.final.json").read_text(encoding="utf-8"))

    tracking_payload = yaml.safe_load(tracking_file.read_text(encoding="utf-8"))
    tracking_payload["social_accounts"].append(
        {
            "item_id": "eastmoney-forum",
            "item_type": "social_account",
            "display_name": "东方财富股吧精选",
            "enabled": True,
            "priority": "core",
            "source_locator": "https://example.com/feeds/eastmoney-forum.xml",
        }
    )
    tracking_payload["commodities"] = [
        item for item in tracking_payload["commodities"] if item["item_id"] != "gold"
    ]
    tracking_file.write_text(yaml.safe_dump(tracking_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    updated_config = load_tracking_config(working_config)
    updated_paths = build_artifact_paths(
        trading_date="2026-04-29-rerun",
        output_dir=tmp_path / "updated" / "report",
        cache_dir=tmp_path / "updated" / "cache",
    )
    updated_result = execute_daily_brief(
        trading_date="2026-04-29-rerun",
        config=updated_config,
        selected_modules=["social_consensus", "research_reports", "commodities"],
        stage="final",
        strict=False,
        artifact_paths=updated_paths,
        mock_data_dir=mock_data_dir,
    )
    assert updated_result["exit_code"] == 0

    updated_report = json.loads((updated_paths.report_dir / "report.final.json").read_text(encoding="utf-8"))
    diff = diff_config_snapshots(
        build_config_snapshot(original_config),
        build_config_snapshot(updated_config),
    )

    assert diff["tracking_changes"]["social_accounts"]["added"] == ["eastmoney-forum"]
    assert diff["tracking_changes"]["commodities"]["removed"] == ["gold"]
    assert set(baseline_report.keys()) == set(updated_report.keys())
    assert set(baseline_report["module_status"].keys()) == set(updated_report["module_status"].keys())
    assert set(baseline_report["coverage_summary"].keys()) == set(updated_report["coverage_summary"].keys())
    assert all(set(section.keys()) == set(updated_report["sections"][0].keys()) for section in updated_report["sections"])