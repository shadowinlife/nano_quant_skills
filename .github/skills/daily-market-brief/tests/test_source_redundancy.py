"""Unit tests for source independence checker (T067, FR-026)."""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from utils.source_independence import check_source_independence


def test_no_violation_when_all_unique():
    entries = [
        {"module": "us_market", "declared_sources": ["us-market-rss"]},
        {"module": "media_mainline", "declared_sources": ["media-mainline-rss"]},
        {"module": "social_consensus", "declared_sources": ["social-tracking-feeds"]},
    ]
    violations = check_source_independence(entries)
    assert violations == []


def test_violation_on_unexpected_shared_source():
    entries = [
        {"module": "us_market", "declared_sources": ["shared-source"]},
        {"module": "social_consensus", "declared_sources": ["shared-source"]},
    ]
    violations = check_source_independence(entries)
    assert len(violations) == 1
    assert "shared-source" in violations[0]
    assert "us_market" in violations[0] or "social_consensus" in violations[0]


def test_allowed_fallback_shared_source_no_violation():
    """us_market ↔ media_mainline share us-market-rss via explicit allowance."""
    entries = [
        {"module": "us_market", "declared_sources": ["us-market-rss"]},
        {"module": "media_mainline", "declared_sources": ["us-market-rss"]},
    ]
    violations = check_source_independence(entries)
    assert violations == []


def test_allowed_reverse_fallback_no_violation():
    entries = [
        {"module": "media_mainline", "declared_sources": ["media-mainline-rss"]},
        {"module": "us_market", "declared_sources": ["media-mainline-rss"]},
    ]
    violations = check_source_independence(entries)
    assert violations == []


def test_empty_entries():
    assert check_source_independence([]) == []


def test_single_module_no_violation():
    entries = [{"module": "us_market", "declared_sources": ["us-market-rss"]}]
    assert check_source_independence(entries) == []


def test_module_with_no_declared_sources():
    entries = [
        {"module": "us_market", "declared_sources": []},
        {"module": "media_mainline", "declared_sources": []},
    ]
    assert check_source_independence(entries) == []


def test_production_module_sources_independent():
    """All 5 default production modules should have no unexpected overlap."""
    entries = [
        {"module": "us_market", "declared_sources": ["us-market-rss"]},
        {"module": "media_mainline", "declared_sources": ["media-mainline-rss"]},
        {"module": "social_consensus", "declared_sources": ["social-tracking-feeds"]},
        {"module": "research_reports", "declared_sources": ["research-tracking-feeds"]},
        {"module": "commodities", "declared_sources": ["commodity-symbol-feed"]},
    ]
    violations = check_source_independence(entries)
    assert violations == []
