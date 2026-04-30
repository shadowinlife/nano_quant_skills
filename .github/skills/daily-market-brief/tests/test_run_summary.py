"""Unit tests for run_summary.py (T056)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from run_summary import write_run_summary


def _minimal_module_entry(module: str = "us_market") -> dict:
    return {
        "module": module,
        "declared_semantic_tag": {"language": "en", "region": "us", "media_type": "newswire"},
        "declared_sources": ["us-market-rss"],
        "attempted_sources": [
            {"url": "us-market-rss", "protocol": "rss", "http_status": None, "records": 2, "fail_class": None}
        ],
        "final_status": "confirmed",
    }


def test_write_run_summary_creates_file(tmp_path):
    path = write_run_summary(
        run_id="2024-01-15:v1",
        trade_date="2024-01-15",
        preflight_ok=True,
        preflight_missing=[],
        module_entries=[_minimal_module_entry()],
        output_dir=tmp_path,
    )
    assert path.exists()
    assert path.name == "run-summary.json"


def test_write_run_summary_content(tmp_path):
    path = write_run_summary(
        run_id="2024-01-15:v1",
        trade_date="2024-01-15",
        preflight_ok=False,
        preflight_missing=["feedparser"],
        module_entries=[_minimal_module_entry()],
        output_dir=tmp_path,
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["run_id"] == "2024-01-15:v1"
    assert doc["preflight"]["ok"] is False
    assert "feedparser" in doc["preflight"]["missing"]
    assert len(doc["modules"]) == 1
    assert doc["modules"][0]["module"] == "us_market"


def test_write_run_summary_coverage_summary(tmp_path):
    path = write_run_summary(
        run_id="2024-01-15:v1",
        trade_date="2024-01-15",
        preflight_ok=True,
        preflight_missing=[],
        module_entries=[],
        output_dir=tmp_path,
        coverage_summary={"covered": 2, "no_new": 1, "source_missing": 0, "list_error": 0, "disabled": 0},
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["coverage_summary"]["covered"] == 2


def test_write_run_summary_creates_parent_dirs(tmp_path):
    nested = tmp_path / "deep" / "nested"
    path = write_run_summary(
        run_id="r1",
        trade_date="2024-01-15",
        preflight_ok=True,
        preflight_missing=[],
        module_entries=[],
        output_dir=nested,
    )
    assert path.exists()


def test_write_run_summary_generated_at_is_iso(tmp_path):
    from datetime import datetime
    path = write_run_summary(
        run_id="r1",
        trade_date="2024-01-15",
        preflight_ok=True,
        preflight_missing=[],
        module_entries=[],
        output_dir=tmp_path,
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    # Should parse without error
    datetime.fromisoformat(doc["generated_at"].replace("Z", "+00:00"))
