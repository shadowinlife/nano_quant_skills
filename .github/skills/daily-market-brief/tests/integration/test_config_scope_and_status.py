from __future__ import annotations

import json
from pathlib import Path

import yaml

from utils.cache_manager import build_artifact_paths
from utils.config_loader import load_tracking_config


def test_every_enabled_tracked_item_receives_an_explicit_status(
    mock_data_dir,
    tmp_path,
    working_config,
) -> None:
    from aggregator import execute_daily_brief

    tracking_file = Path(working_config).with_name("tracking-lists.yaml")
    tracking_payload = yaml.safe_load(tracking_file.read_text(encoding="utf-8"))
    tracking_payload["research_institutions"].append(
        {
            "item_id": "huaan",
            "item_type": "research_institution",
            "display_name": "华安证券研究",
            "enabled": True,
            "priority": "core",
            "source_locator": "https://feeds.stub.local/research/huaan.rss",
            "region": "CN",
        }
    )
    tracking_file.write_text(yaml.safe_dump(tracking_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    config = load_tracking_config(working_config)
    artifact_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "scope" / "report",
        cache_dir=tmp_path / "scope" / "cache",
    )

    result = execute_daily_brief(
        trading_date="2026-04-29",
        config=config,
        selected_modules=["social_consensus", "research_reports", "commodities"],
        stage="final",
        strict=False,
        artifact_paths=artifact_paths,
        mock_data_dir=mock_data_dir,
    )

    assert result["exit_code"] == 0

    seen_statuses: dict[str, str] = {}
    for file_path in artifact_paths.module_results_dir.glob("*.final.json"):
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        for entry in payload["tracking_coverage"]:
            seen_statuses[entry["item_id"]] = entry["status"]

    enabled_item_ids = {
        item.item_id
        for item in config.social_accounts + config.research_institutions + config.commodities
        if item.enabled
    }
    assert enabled_item_ids.issubset(seen_statuses)
    assert set(seen_statuses.values()).issubset(
        {"covered", "no_new", "source_missing", "list_error", "disabled"}
    )