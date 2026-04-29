from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import feedparser
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent.
    feedparser = None

try:
    import requests
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent.
    requests = None


def load_mock_records(mock_data_dir: str | Path | None, file_name: str) -> list[dict[str, Any]]:
    if not mock_data_dir:
        return []
    path = Path(mock_data_dir).resolve() / file_name
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("records", []))


def fetch_rss_records(
    feeds: list[dict[str, str]],
    limit: int = 5,
) -> dict[str, Any]:
    if feedparser is None or requests is None:
        return {
            "records": [],
            "source_state": "source_missing",
            "note": "Optional live-feed dependencies are unavailable",
        }

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for feed in feeds:
        url = feed["url"]
        source_name = feed["source_name"]
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            entries = getattr(parsed, "entries", []) or []
            for entry in entries[:limit]:
                headline = str(entry.get("title", "")).strip()
                if not headline:
                    continue
                records.append(
                    {
                        "topic_id": str(entry.get("id") or entry.get("link") or headline),
                        "headline": headline,
                        "summary": str(entry.get("summary") or headline).strip(),
                        "published_at": str(entry.get("published") or entry.get("updated") or ""),
                        "url": str(entry.get("link") or url),
                        "source_name": source_name,
                        "confidence": "medium",
                    }
                )
        except Exception as exc:
            errors.append(f"{source_name}: {exc}")

    if records:
        return {
            "records": records[:limit],
            "source_state": "ok",
            "note": "",
        }
    return {
        "records": [],
        "source_state": "source_missing",
        "note": "; ".join(errors) if errors else "No live records fetched",
    }


def fetch_tracking_feed_records(
    tracking_items,
    limit_per_item: int = 3,
) -> dict[str, Any]:
    if feedparser is None or requests is None:
        return {
            "records": [],
            "source_state": "source_missing",
            "note": "Optional live-feed dependencies are unavailable",
        }

    feeds = []
    for item in tracking_items:
        if not item.enabled:
            continue
        if str(item.source_locator).startswith("http"):
            feeds.append(
                {
                    "url": item.source_locator,
                    "source_name": item.display_name,
                    "item_id": item.item_id,
                }
            )
    if not feeds:
        return {
            "records": [],
            "source_state": "source_missing",
            "note": "No HTTP-based live feeds configured for tracking items",
        }

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for feed in feeds:
        try:
            response = requests.get(feed["url"], timeout=10)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            entries = getattr(parsed, "entries", []) or []
            for entry in entries[:limit_per_item]:
                headline = str(entry.get("title", "")).strip()
                if not headline:
                    continue
                records.append(
                    {
                        "item_id": feed["item_id"],
                        "topic_id": str(entry.get("id") or entry.get("link") or headline),
                        "headline": headline,
                        "summary": str(entry.get("summary") or headline).strip(),
                        "published_at": str(entry.get("published") or entry.get("updated") or ""),
                        "url": str(entry.get("link") or feed["url"]),
                        "source_name": feed["source_name"],
                        "confidence": "medium",
                    }
                )
        except Exception as exc:
            errors.append(f"{feed['source_name']}: {exc}")

    if records:
        return {"records": records, "source_state": "ok", "note": ""}
    return {
        "records": [],
        "source_state": "source_missing",
        "note": "; ".join(errors) if errors else "Tracking feeds returned no records",
    }