from __future__ import annotations

from models import TrackingItem
from modules.common import build_module_result


def test_tracking_module_source_missing_summary_is_not_reported_as_no_new() -> None:
    result = build_module_result(
        run_id="demo-run",
        module="commodities",
        stage="final",
        time_window={"label": "近三个交易日"},
        source_payload={
            "records": [],
            "source_state": "source_missing",
            "note": "Commodity live adapter is not configured for symbol-based mockless execution yet",
        },
        tracking_items=[
            TrackingItem(
                item_id="brent",
                item_type="commodity",
                display_name="布伦特原油",
                enabled=True,
                priority="core",
                source_locator="BRENT",
            )
        ],
    )

    assert result.status == "missing"
    assert "来源不可用" in result.summary
    assert "无新增" not in result.summary


def test_anomaly_flags_raise_review_required_status() -> None:
    result = build_module_result(
        run_id="demo-run",
        module="social_consensus",
        stage="final",
        time_window={"label": "近五个交易日"},
        source_payload={
            "records": [
                {
                    "item_id": "xueqiu-hot",
                    "topic_id": "social-001",
                    "headline": "社媒观点出现明显冲突",
                    "summary": "同一主题在核心账号之间出现相反结论。",
                    "anomaly_flags": ["conflicting_social_consensus"],
                    "review_required": True,
                    "conflict_state": "needs_review",
                }
            ],
            "source_state": "ok",
        },
        tracking_items=[
            TrackingItem(
                item_id="xueqiu-hot",
                item_type="social_account",
                display_name="雪球热帖",
                enabled=True,
                priority="core",
                source_locator="https://example.com/feeds/xueqiu-hot.xml",
            )
        ],
    )

    assert result.status == "review_required"
    assert result.manual_review_required is True
    assert result.anomaly_flags == ["conflicting_social_consensus", "social-001"]
    assert result.highlights[0].conflict_state == "needs_review"