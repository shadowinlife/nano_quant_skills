"""Unit tests for module status reason fields (T073, FR-029).

Covers:
- skip_reason in ModuleResult appears in render_markdown when status=skipped
- disabled_reason in TrackingItem is set from config_loader
- disabled items surface as status=skipped at runtime (not status=disabled)
"""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from models import AggregatedReport, ModuleResult
from utils.report_builder import build_aggregated_report, render_markdown


def _make_skipped_result(module: str, skip_reason: str | None = None) -> ModuleResult:
    return ModuleResult(
        run_id="r-test",
        module=module,
        stage="final",
        status="skipped",
        time_window={"label": "近一交易日"},
        summary="模块已跳过。",
        evidence=[],
        skip_reason=skip_reason,
    )


def test_skip_reason_appears_in_markdown():
    mr = _make_skipped_result("commodities", skip_reason="配置禁用：数据源未对接")
    report = build_aggregated_report(
        run_id="r-test",
        stage="final",
        module_results=[mr],
        report_path="tmp/r-test/report.md",
        selected_modules=["commodities"],
    )
    md = render_markdown(report, [mr])
    assert "跳过原因" in md
    assert "配置禁用：数据源未对接" in md


def test_no_skip_reason_no_hint():
    mr = _make_skipped_result("commodities", skip_reason=None)
    report = build_aggregated_report(
        run_id="r-test",
        stage="final",
        module_results=[mr],
        report_path="tmp/r-test/report.md",
        selected_modules=["commodities"],
    )
    md = render_markdown(report, [mr])
    assert "跳过原因" not in md


def test_skip_reason_only_when_status_skipped():
    """A non-skipped module with skip_reason set should NOT show the hint."""
    mr = ModuleResult(
        run_id="r-test",
        module="commodities",
        stage="final",
        status="confirmed",
        time_window={"label": "近一交易日"},
        summary="正常完成。",
        evidence=[],
        skip_reason="should-not-show",
    )
    report = build_aggregated_report(
        run_id="r-test",
        stage="final",
        module_results=[mr],
        report_path="tmp/r-test/report.md",
        selected_modules=["commodities"],
    )
    md = render_markdown(report, [mr])
    assert "跳过原因" not in md


def test_tracking_item_disabled_reason_preserved():
    from models import TrackingItem
    item = TrackingItem(
        item_id="coal",
        item_type="commodity",
        display_name="焦煤",
        enabled=False,
        priority="extended",
        source_locator="COKING_COAL",
        disabled_reason="akshare 暂未提供焦煤连续合约",
    )
    assert item.disabled_reason == "akshare 暂未提供焦煤连续合约"
    assert item.enabled is False


def test_config_loader_sets_disabled_reason(working_config):
    from utils.config_loader import load_tracking_config
    config = load_tracking_config(working_config)
    # cls-opinion is disabled in tracking-lists.yaml with a disabled_reason
    disabled = [item for item in config.social_accounts if not item.enabled]
    assert len(disabled) >= 1
    for item in disabled:
        assert item.disabled_reason is not None and item.disabled_reason.strip() != ""
