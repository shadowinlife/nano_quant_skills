from __future__ import annotations

from typing import Any

from .common import fetch_rss_records
from .common import load_mock_records


US_MARKET_FEEDS = [
    {
        "url": "https://feeds.marketwatch.com/marketwatch/marketpulse/",
        "source_name": "MarketWatch MarketPulse",
    },
    {
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "source_name": "WSJ Markets",
    },
]


def fetch_us_market_data(
    trading_date: str,
    *,
    mock_data_dir=None,
    source_tier: str = "production",
) -> dict[str, Any]:
    records = load_mock_records(mock_data_dir, "us_market.json")
    if records:
        return {"records": records, "source_state": "ok", "note": "mock_data"}
    if source_tier != "production":
        return {"records": [], "source_state": "source_missing", "note": "Exploration tier disabled"}
    return fetch_rss_records(US_MARKET_FEEDS)