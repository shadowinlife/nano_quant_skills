from __future__ import annotations

from typing import Any

from .common import load_mock_records


def _fetch_one_commodity(item) -> dict[str, Any] | None:
    """Pull two most recent bars via akshare and synthesize a price-change record."""
    try:
        import akshare as ak
    except ImportError:
        return None
    symbol = str(item.source_locator).strip()
    if not symbol:
        return None
    try:
        df = ak.futures_foreign_hist(symbol=symbol)
    except Exception as exc:
        return {
            "item_id": item.item_id,
            "topic_id": f"{item.item_id}-error",
            "headline": f"{item.display_name} 行情拉取失败",
            "summary": f"akshare futures_foreign_hist({symbol}) 失败: {exc}",
            "source_name": f"akshare:{symbol}",
            "confidence": "low",
            "review_required": True,
        }
    if df is None or df.empty or len(df) < 2:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2]
    try:
        last_close = float(last["close"])
        prev_close = float(prev["close"])
    except Exception:
        return None
    change = last_close - prev_close
    pct = (change / prev_close * 100.0) if prev_close else 0.0
    direction = "上涨" if change > 0 else ("下跌" if change < 0 else "持平")
    last_date = last.get("date")
    last_date_str = str(last_date.date()) if hasattr(last_date, "date") else str(last_date)
    headline = f"{item.display_name} 收报 {last_close:.2f}（较前一交易日{direction} {abs(pct):.2f}%）"
    summary = f"{last_date_str} 收盘 {last_close:.2f}，较前一交易日 {prev_close:.2f} {direction} {abs(change):.2f}（{abs(pct):.2f}%）。"

    # Compute session gap for FR-024 trade date provenance
    session_gap: int | None = None
    try:
        from datetime import date as _date
        if isinstance(last_date, _date):
            target = _date.fromisoformat(item.metadata.get("trading_date", last_date_str))
        else:
            target = _date.fromisoformat(str(last_date_str))
        gap = abs((target - (last_date if isinstance(last_date, _date) else _date.fromisoformat(last_date_str))).days)
        if gap > 5:
            session_gap = gap
    except Exception:
        pass

    record: dict[str, Any] = {
        "item_id": item.item_id,
        "topic_id": f"{item.item_id}-{last_date_str}",
        "headline": headline,
        "summary": summary,
        "published_at": last_date_str,
        "url": "",
        "source_name": f"akshare:{symbol}",
        "confidence": "high",
        "trade_date": last_date_str,
    }
    if session_gap is not None:
        record["previous_session_gap_days"] = session_gap
    return record


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
    if source_tier != "production":
        return {
            "records": [],
            "source_state": "source_missing",
            "note": "Exploration tier disabled",
        }
    live_records: list[dict[str, Any]] = []
    errors: list[str] = []
    for item in tracking_items:
        if not item.enabled:
            continue
        try:
            rec = _fetch_one_commodity(item)
        except Exception as exc:
            errors.append(f"{item.display_name}: {exc}")
            continue
        if rec:
            live_records.append(rec)
    if live_records:
        return {
            "records": live_records,
            "source_state": "ok",
            "note": "akshare:futures_foreign_hist" + (f"; errors: {'; '.join(errors)}" if errors else ""),
        }
    return {
        "records": [],
        "source_state": "source_missing",
        "note": "; ".join(errors) if errors else "No commodity records fetched",
    }
