from __future__ import annotations

from typing import Any

from .common import fetch_tracking_feed_records
from .common import load_mock_records


def fetch_research_reports_data(
    tracking_items,
    trading_date: str,
    *,
    mock_data_dir=None,
    source_tier: str = "production",
) -> dict[str, Any]:
    records = load_mock_records(mock_data_dir, "research_reports.json")
    if records:
        return {"records": records, "source_state": "ok", "note": "mock_data"}
    if source_tier != "production":
        return {"records": [], "source_state": "source_missing", "note": "Exploration tier disabled"}
    return fetch_tracking_feed_records(tracking_items)