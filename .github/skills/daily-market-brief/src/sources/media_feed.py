from __future__ import annotations

from typing import Any

from .common import fetch_rss_records
from .common import load_mock_records


MEDIA_MAINLINE_FEEDS = [
    {
        "url": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "source_name": "WSJ Markets",
    },
]


def _fetch_caixin_main_news(limit: int = 5) -> dict[str, Any]:
    """Fallback to akshare's Caixin main news when RSS feeds are unavailable."""
    try:
        import akshare as ak
    except ImportError:
        return {
            "records": [],
            "source_state": "source_missing",
            "note": "akshare not installed for media_mainline fallback",
        }
    try:
        df = ak.stock_news_main_cx()
    except Exception as exc:
        return {
            "records": [],
            "source_state": "source_missing",
            "note": f"akshare stock_news_main_cx failed: {exc}",
        }
    if df is None or df.empty:
        return {
            "records": [],
            "source_state": "source_missing",
            "note": "akshare stock_news_main_cx returned empty",
        }
    records: list[dict[str, Any]] = []
    for index, row in df.head(limit).iterrows():
        summary = str(row.get("summary") or "").strip()
        tag = str(row.get("tag") or "").strip()
        url = str(row.get("url") or "").strip()
        headline = summary.split("。")[0][:80] if summary else (tag or f"caixin-{index}")
        records.append(
            {
                "topic_id": url or f"caixin-{index}",
                "headline": headline,
                "summary": summary or headline,
                "published_at": "",
                "url": url,
                "source_name": f"财新数据通 / {tag}" if tag else "财新数据通",
                "confidence": "medium",
            }
        )
    return {"records": records, "source_state": "ok", "note": "akshare:stock_news_main_cx"}


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
    rss_payload = fetch_rss_records(MEDIA_MAINLINE_FEEDS)
    if rss_payload.get("records"):
        return rss_payload
    fallback = _fetch_caixin_main_news()
    if fallback.get("records"):
        return fallback
    return rss_payload
