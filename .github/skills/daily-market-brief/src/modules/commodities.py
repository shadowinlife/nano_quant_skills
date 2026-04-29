from __future__ import annotations

from models import TrackingConfig
from sources import fetch_commodity_data

from .common import build_module_result


def run_commodities_module(
    run_id: str,
    trading_date: str,
    config: TrackingConfig,
    *,
    stage: str,
    mock_data_dir=None,
):
    payload = fetch_commodity_data(
        config.commodities,
        trading_date,
        mock_data_dir=mock_data_dir,
        source_tier=config.source_tiers.get("commodities", "production"),
    )
    return build_module_result(
        run_id=run_id,
        module="commodities",
        stage=stage,
        time_window=config.time_windows["commodities"],
        source_payload=payload,
        tracking_items=config.commodities,
    )