from __future__ import annotations

from typing import Any

from .common import fetch_rss_records
from .common import load_mock_records


MEDIA_MAINLINE_FEEDS = [
    {
        "url": "https://finance.sina.com.cn/rss/finance.xml",
        "source_name": "新浪财经",
    },
    {
        "url": "https://www.cls.cn/rss/news.xml",
        "source_name": "财联社",
    },
]


def fetch_media_mainline_data(
    trading_date: str,
    *,
    mock_data_dir=None,
    source_tier: str = "production",
) -> dict[str, Any]:
    records = load_mock_records(mock_data_dir, "media_mainline.json")
    if records:
        return {"records": records, "source_state": "ok", "note": "mock_data"}
    if source_tier != "production":
        return {"records": [], "source_state": "source_missing", "note": "Exploration tier disabled"}
    return fetch_rss_records(MEDIA_MAINLINE_FEEDS)