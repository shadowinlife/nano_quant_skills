from __future__ import annotations

from models import TrackingConfig
from sources import fetch_us_market_data

from .common import build_module_result


def run_us_market_module(
    run_id: str,
    trading_date: str,
    config: TrackingConfig,
    *,
    stage: str,
    mock_data_dir=None,
):
    payload = fetch_us_market_data(
        trading_date,
        mock_data_dir=mock_data_dir,
        source_tier=config.source_tiers.get("us_market", "production"),
    )
    return build_module_result(
        run_id=run_id,
        module="us_market",
        stage=stage,
        time_window=config.time_windows["us_market"],
        source_payload=payload,
    )