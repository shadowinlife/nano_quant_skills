from __future__ import annotations

from models import TrackingConfig
from sources import fetch_social_consensus_data

from .common import build_module_result


def run_social_consensus_module(
    run_id: str,
    trading_date: str,
    config: TrackingConfig,
    *,
    stage: str,
    mock_data_dir=None,
):
    payload = fetch_social_consensus_data(
        config.social_accounts,
        trading_date,
        mock_data_dir=mock_data_dir,
        source_tier=config.source_tiers.get("social_consensus", "production"),
    )
    return build_module_result(
        run_id=run_id,
        module="social_consensus",
        stage=stage,
        time_window=config.time_windows["social_consensus"],
        source_payload=payload,
        tracking_items=config.social_accounts,
    )