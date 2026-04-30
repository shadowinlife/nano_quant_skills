"""Unit tests for preflight.py (T054)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from preflight import PreflightResult, check_config_file, check_deps, run_preflight


def test_preflight_result_ok():
    pf = PreflightResult(ok=True, missing=[])
    assert pf.ok
    assert pf.missing == []
    assert pf.stderr_line() is None


def test_preflight_result_fail():
    pf = PreflightResult(ok=False, missing=["yaml", "feedparser"])
    assert not pf.ok
    line = pf.stderr_line()
    assert line is not None
    assert "PREFLIGHT_FAIL:" in line
    assert "yaml" in line
    assert "feedparser" in line


def test_preflight_as_dict():
    pf = PreflightResult(ok=False, missing=["yaml"])
    d = pf.as_dict()
    assert d == {"ok": False, "missing": ["yaml"]}


def test_check_deps_known_packages():
    # yaml, feedparser, jsonschema, requests should all be importable in the test env
    missing = check_deps()
    assert missing == [], f"Expected no missing deps, got: {missing}"


def test_check_deps_missing_package():
    missing = check_deps(extra=["this_package_does_not_exist_xyz"])
    assert "this_package_does_not_exist_xyz" in missing


def test_check_config_file_missing(tmp_path):
    issues = check_config_file(tmp_path / "nonexistent.yaml")
    assert len(issues) == 1
    assert "config_file_missing" in issues[0]


def test_check_config_file_exists(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("version: 1\n", encoding="utf-8")
    issues = check_config_file(cfg)
    assert issues == []


def test_run_preflight_pass(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("version: 1\n", encoding="utf-8")
    result = run_preflight(config_path=cfg)
    assert result.ok


def test_run_preflight_fail_missing_config(tmp_path):
    result = run_preflight(config_path=tmp_path / "no_such.yaml")
    assert not result.ok
    assert any("config_file_missing" in m for m in result.missing)


def test_run_preflight_no_config_still_checks_deps():
    result = run_preflight()
    # Should pass because all deps are installed in test env
    assert result.ok
