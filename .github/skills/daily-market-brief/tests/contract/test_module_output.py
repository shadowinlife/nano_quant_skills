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