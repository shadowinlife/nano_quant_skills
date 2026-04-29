from __future__ import annotations

from typing import Any

from .common import load_mock_records


def fetch_commodity_data(
    tracking_items,
    trading_date: str,
    *,
    mock_data_dir=None,
    source_tier: str = "production",
) -> dict[str, Any]:
    records = load_mock_records(mock_data_dir, "commodities.json")
    if records:
        return {"records": records, "source_state": "ok", "note": "mock_data"}
    return {
        "records": [],
        "source_state": "source_missing",
        "note": "Commodity live adapter is not configured for symbol-based mockless execution yet",
    }