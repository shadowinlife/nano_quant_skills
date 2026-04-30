from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from models import CoverageStatus
from models import EvidenceRecord
from models import HighlightTopic
from models import ModuleResult


REPO_ROOT = Path(__file__).resolve().parents[5]
SCHEMA_PATH = REPO_ROOT / "specs" / "001-daily-market-brief" / "contracts" / "module-result.schema.json"


def test_module_result_matches_contract_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = ModuleResult(
        run_id="2026-04-29:demo",
        module="social_consensus",
        stage="final",
        status="confirmed",
        time_window={"label": "近五个交易日"},
        summary="社媒讨论集中在高股息与顺周期切换。",
        highlights=[
            HighlightTopic(
                topic_id="social-001",
                title="高股息切换",
                summary="高股息切换成为社媒主流共识。",
                priority_rank=1,
                confidence="high",
            )
        ],
        tracking_coverage=[
            CoverageStatus(
                item_id="xueqiu-hot",
                display_name="雪球热帖",
                status="covered",
                evidence_count=1,
            )
        ],
        evidence=[
            EvidenceRecord(
                evidence_id="ev-social-001",
                source_name="雪球热帖",
                source_tier="production",
                headline="高股息切换",
                url="https://example.com/social-001",
            )
        ],
    ).to_dict()

    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    assert errors == []


def test_module_result_requires_anomaly_flags_for_review_items() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = ModuleResult(
        run_id="2026-04-29:demo",
        module="research_reports",
        stage="final",
        status="review_required",
        time_window={"label": "近五个交易日"},
        summary="研报出现明显分歧，需要人工复核。",
        highlights=[],
        tracking_coverage=[],
        evidence=[],
        manual_review_required=True,
    ).to_dict()

    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    assert any("anomaly_flags" in error.message for error in errors)


def test_module_result_with_semantic_drift_validates() -> None:
    """FR-023: semantic_drift field is accepted by the schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = ModuleResult(
        run_id="2026-04-29:demo",
        module="us_market",
        stage="final",
        status="confirmed",
        time_window={"label": "近一个交易日"},
        summary="美股科技板块普涨，情绪偏乐观。",
        highlights=[],
        tracking_coverage=[],
        evidence=[],
        semantic_drift={
            "declared": {"language": "en", "region": "us", "media_type": "newswire"},
            "observed": {"language": "zh", "region": "cn", "media_type": "newswire"},
            "drift_categories": ["language", "region"],
        },
        attempted_source_ids=["us-market-rss"],
    ).to_dict()
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    assert errors == []


def test_module_result_with_evidence_trade_date_validates() -> None:
    """FR-024: trade_date and previous_session_gap_days on evidence are accepted."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    payload = ModuleResult(
        run_id="2026-04-29:demo",
        module="commodities",
        stage="final",
        status="confirmed",
        time_window={"label": "近一个交易日"},
        summary="原油价格下跌，黄金小幅上涨。",
        highlights=[],
        tracking_coverage=[],
        evidence=[
            EvidenceRecord(
                evidence_id="ev-oil-001",
                source_name="akshare:CL",
                source_tier="production",
                headline="原油 收报 75.00",
                trade_date="2024-01-12",
                previous_session_gap_days=3,
            )
        ],
    ).to_dict()
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    assert errors == []