from __future__ import annotations

from models import TrackingConfig
from sources import fetch_media_mainline_data

from .common import build_module_result


def run_media_mainline_module(
    run_id: str,
    trading_date: str,
    config: TrackingConfig,
    *,
    stage: str,
    mock_data_dir=None,
):
    payload = fetch_media_mainline_data(
        trading_date,
        mock_data_dir=mock_data_dir,
        source_tier=config.source_tiers.get("media_mainline", "production"),
    )
    return build_module_result(
        run_id=run_id,
        module="media_mainline",
        stage=stage,
        time_window=config.time_windows["media_mainline"],
        source_payload=payload,
    )