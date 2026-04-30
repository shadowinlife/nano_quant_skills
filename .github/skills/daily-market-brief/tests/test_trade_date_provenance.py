"""Unit tests for trade date provenance (T063, FR-024)."""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from models import EvidenceRecord


def test_evidence_record_accepts_trade_date():
    ev = EvidenceRecord(
        evidence_id="ev-001",
        source_name="akshare:CL",
        source_tier="production",
        headline="原油行情",
        trade_date="2024-01-10",
    )
    assert ev.trade_date == "2024-01-10"
    assert ev.previous_session_gap_days is None


def test_evidence_record_gap_days():
    ev = EvidenceRecord(
        evidence_id="ev-002",
        source_name="akshare:GC",
        source_tier="production",
        headline="黄金行情",
        trade_date="2024-01-05",
        previous_session_gap_days=10,
    )
    assert ev.previous_session_gap_days == 10


def test_evidence_record_to_dict_includes_trade_date():
    ev = EvidenceRecord(
        evidence_id="ev-003",
        source_name="akshare:CL",
        source_tier="production",
        headline="原油行情",
        trade_date="2024-01-10",
        previous_session_gap_days=7,
    )
    d = ev.to_dict()
    assert d["trade_date"] == "2024-01-10"
    assert d["previous_session_gap_days"] == 7


def test_evidence_record_to_dict_omits_none_trade_date():
    ev = EvidenceRecord(
        evidence_id="ev-004",
        source_name="source",
        source_tier="production",
        headline="headline",
    )
    d = ev.to_dict()
    assert "trade_date" not in d
    assert "previous_session_gap_days" not in d


def test_build_module_result_propagates_trade_date():
    from modules.common import build_module_result

    payload = {
        "records": [
            {
                "evidence_id": "ev-001",
                "headline": "原油 75.00",
                "source_name": "akshare:CL",
                "trade_date": "2024-01-10",
                "previous_session_gap_days": 8,
            }
        ],
        "source_state": "ok",
        "note": "",
    }
    result = build_module_result(
        run_id="r1",
        module="commodities",
        stage="final",
        time_window={"label": "近一交易日"},
        source_payload=payload,
    )
    assert len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.trade_date == "2024-01-10"
    assert ev.previous_session_gap_days == 8


def test_markdown_shows_lag_hint_when_gap_present():
    from models import AggregatedReport, HighlightTopic, ModuleResult
    from utils.report_builder import build_aggregated_report, render_markdown

    ev = EvidenceRecord(
        evidence_id="ev-001",
        source_name="akshare:CL",
        source_tier="production",
        headline="原油 75.00",
        trade_date="2024-01-08",
        previous_session_gap_days=7,
    )
    module_result = ModuleResult(
        run_id="r1",
        module="commodities",
        stage="final",
        status="confirmed",
        time_window={"label": "近一交易日"},
        summary="原油价格下跌。",
        evidence=[ev],
    )
    report = build_aggregated_report(
        run_id="r1",
        stage="final",
        module_results=[module_result],
        report_path="tmp/r1/report.md",
        selected_modules=["commodities"],
    )
    md = render_markdown(report, [module_result])
    assert "行情滞后" in md
