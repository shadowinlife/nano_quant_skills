"""Unit tests for stage coverage consistency (T069, FR-028)."""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from utils.report_builder import build_coverage_summary, build_aggregated_report
from models import ModuleResult


def _make_module_result(module: str, status: str = "confirmed") -> ModuleResult:
    return ModuleResult(
        run_id="r-test",
        module=module,
        stage="final",
        status=status,
        time_window={"label": "近一交易日"},
        summary=f"{module} summary.",
        evidence=[],
    )


def test_canonical_keys_present_in_empty_run():
    """build_coverage_summary always includes the 5 canonical keys."""
    result = build_coverage_summary([])
    canonical = {"covered", "no_new", "source_missing", "list_error", "disabled"}
    assert set(result.keys()) == canonical


def test_coverage_summary_counts():
    from models import CoverageStatus
    mr = _make_module_result("us_market")
    mr.tracking_coverage = [
        CoverageStatus(item_id="a", display_name="A", status="covered", evidence_count=2),
        CoverageStatus(item_id="b", display_name="B", status="no_new", evidence_count=0),
        CoverageStatus(item_id="c", display_name="C", status="covered", evidence_count=1),
    ]
    summary = build_coverage_summary([mr])
    assert summary["covered"] == 2
    assert summary["no_new"] == 1
    assert summary["source_missing"] == 0


def test_coverage_keys_stable_across_stages():
    """Final report coverage_summary contains exactly the 5 canonical keys."""
    mr = _make_module_result("us_market")
    report = build_aggregated_report(
        run_id="r-test",
        stage="final",
        module_results=[mr],
        report_path="tmp/r-test/report.md",
        selected_modules=["us_market"],
    )
    canonical = {"covered", "no_new", "source_missing", "list_error", "disabled"}
    assert set(report.coverage_summary.keys()) == canonical


def test_coverage_summary_additive_across_modules():
    from models import CoverageStatus
    mr1 = _make_module_result("us_market")
    mr1.tracking_coverage = [
        CoverageStatus(item_id="a", display_name="A", status="covered", evidence_count=1),
    ]
    mr2 = _make_module_result("media_mainline")
    mr2.tracking_coverage = [
        CoverageStatus(item_id="b", display_name="B", status="disabled", evidence_count=0),
    ]
    summary = build_coverage_summary([mr1, mr2])
    assert summary["covered"] == 1
    assert summary["disabled"] == 1


def test_coverage_no_extra_keys():
    """build_coverage_summary never introduces keys beyond the 5 canonical ones."""
    from models import CoverageStatus
    mr = _make_module_result("commodities")
    mr.tracking_coverage = [
        CoverageStatus(item_id="x", display_name="X", status="list_error", evidence_count=0),
    ]
    summary = build_coverage_summary([mr])
    unexpected = set(summary.keys()) - {"covered", "no_new", "source_missing", "list_error", "disabled"}
    assert unexpected == set()
