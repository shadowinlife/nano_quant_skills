from __future__ import annotations

from models import TrackingConfig
from sources import fetch_research_reports_data

from .common import build_module_result


def run_research_reports_module(
    run_id: str,
    trading_date: str,
    config: TrackingConfig,
    *,
    stage: str,
    mock_data_dir=None,
):
    payload = fetch_research_reports_data(
        config.research_institutions,
        trading_date,
        mock_data_dir=mock_data_dir,
        source_tier=config.source_tiers.get("research_reports", "production"),
    )
    return build_module_result(
        run_id=run_id,
        module="research_reports",
        stage=stage,
        time_window=config.time_windows["research_reports"],
        source_payload=payload,
        tracking_items=config.research_institutions,
    )