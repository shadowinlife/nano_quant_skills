from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from models import CoverageStatus
from models import EvidenceRecord
from models import HighlightTopic
from models import ModuleResult
from utils.report_builder import build_aggregated_report


REPO_ROOT = Path(__file__).resolve().parents[5]
SCHEMA_PATH = REPO_ROOT / "specs" / "001-daily-market-brief" / "contracts" / "aggregated-report.schema.json"


def _sample_results() -> list[ModuleResult]:
    return [
        ModuleResult(
            run_id="2026-04-29:demo",
            module="us_market",
            stage="temp",
            status="confirmed",
            time_window={"label": "前一交易日至开盘前"},
            summary="美股科技股走强，风险偏好有所回暖。",
            highlights=[
                HighlightTopic(
                    topic_id="us-001",
                    title="科技股走强",
                    summary="科技股走强带动风险偏好回升。",
                    priority_rank=1,
                    confidence="high",
                    module_origins=["us_market"],
                )
            ],
            tracking_coverage=[],
            evidence=[
                EvidenceRecord(
                    evidence_id="ev-us-001",
                    source_name="US Feed",
                    source_tier="production",
                    headline="科技股走强",
                )
            ],
        ),
        ModuleResult(
            run_id="2026-04-29:demo",
            module="commodities",
            stage="temp",
            status="missing",
            time_window={"label": "近三个交易日"},
            summary="商品模块本轮未拿到稳定新增。",
            highlights=[],
            tracking_coverage=[
                CoverageStatus(
                    item_id="brent",
                    display_name="布伦特原油",
                    status="source_missing",
                    evidence_count=0,
                )
            ],
            evidence=[],
        ),
    ]


def test_aggregated_report_matches_contract_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    report = build_aggregated_report(
        run_id="2026-04-29:demo",
        stage="temp",
        module_results=_sample_results(),
        report_path="tmp/2026-04-29/report/report.temp.md",
        selected_modules=["us_market", "commodities"],
    ).to_dict()

    errors = sorted(validator.iter_errors(report), key=lambda item: item.path)
    assert errors == []
    assert len(report["top_highlights"]) <= 5
    assert len(report["sections"]) <= 10


def test_aggregated_report_with_run_summary_path_validates() -> None:
    """FR-027 (T047): run_summary_path on AggregatedReport is accepted by schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    report = build_aggregated_report(
        run_id="2026-04-29:demo",
        stage="final",
        module_results=_sample_results(),
        report_path="tmp/2026-04-29/report/report.final.md",
        selected_modules=["us_market", "commodities"],
    )
    report.run_summary_path = "tmp/2026-04-29/run-summary.json"
    payload = report.to_dict()
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.path)
    assert errors == []
    assert payload.get("run_summary_path") == "tmp/2026-04-29/run-summary.json"