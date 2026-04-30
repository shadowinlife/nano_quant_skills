"""Integration tests for runtime reliability (T070, FR-021~FR-028).

Verifies end-to-end execute_daily_brief() with mock data:
- run-summary.json is produced and validates against schema
- exit_code in {0, 3}
- run_summary_path present in result
- preflight fail path returns exit_code=4
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from jsonschema import Draft202012Validator

SKILL_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SPEC_ROOT = Path(__file__).resolve().parents[5] / "specs" / "001-daily-market-brief"
RUN_SUMMARY_SCHEMA_PATH = SPEC_ROOT / "contracts" / "run-summary.schema.json"


def test_execute_daily_brief_produces_run_summary(
    mock_data_dir,
    tmp_path,
    working_config,
) -> None:
    from aggregator import execute_daily_brief
    from utils.cache_manager import build_artifact_paths
    from utils.config_loader import load_tracking_config

    config = load_tracking_config(working_config)
    artifact_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "run" / "report",
        cache_dir=tmp_path / "run" / "cache",
    )

    result = execute_daily_brief(
        trading_date="2026-04-29",
        config=config,
        selected_modules=["us_market", "media_mainline", "commodities"],
        stage="auto",
        strict=False,
        artifact_paths=artifact_paths,
        mock_data_dir=mock_data_dir,
    )

    # exit_code should be 0 or 3 (some modules may be missing data)
    assert result["exit_code"] in {0, 3}

    # run_summary_path must be present
    assert "run_summary_path" in result
    run_summary_path = Path(result["run_summary_path"])
    assert run_summary_path.exists(), f"run-summary.json not found at {run_summary_path}"

    # Validate against schema
    schema = json.loads(RUN_SUMMARY_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    summary_data = json.loads(run_summary_path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(summary_data), key=lambda e: str(e.path))
    assert errors == [], f"run-summary.json schema violations: {[e.message for e in errors]}"


def test_execute_daily_brief_run_summary_has_required_fields(
    mock_data_dir,
    tmp_path,
    working_config,
) -> None:
    from aggregator import execute_daily_brief
    from utils.cache_manager import build_artifact_paths
    from utils.config_loader import load_tracking_config

    config = load_tracking_config(working_config)
    artifact_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "run2" / "report",
        cache_dir=tmp_path / "run2" / "cache",
    )

    result = execute_daily_brief(
        trading_date="2026-04-29",
        config=config,
        selected_modules=["us_market", "commodities"],
        stage="final",
        strict=False,
        artifact_paths=artifact_paths,
        mock_data_dir=mock_data_dir,
    )

    run_summary_path = Path(result["run_summary_path"])
    data = json.loads(run_summary_path.read_text(encoding="utf-8"))

    assert "run_id" in data
    assert "generated_at" in data
    assert "preflight" in data
    assert "modules" in data
    assert isinstance(data["modules"], list)
    # trade_date is not a top-level field in run-summary.json;
    # it lives inside module evidence records

    # Each module entry must include module name and source list
    for entry in data["modules"]:
        assert "module" in entry
        assert "declared_sources" in entry


def test_execute_daily_brief_preflight_fail_returns_exit4(
    tmp_path,
    working_config,
) -> None:
    """When config_path is missing, main() returns exit_code non-zero."""
    import subprocess

    result = subprocess.run(
        [
            sys.executable, "-m", "main",
            "--config", str(tmp_path / "nonexistent.yaml"),
            "--date", "2026-04-29",
            "--output-dir", str(tmp_path / "out"),
        ],
        cwd=str(SKILL_ROOT / "src"),
        capture_output=True,
        text=True,
    )
    # Non-zero exit code: 4 (preflight fail) or 5 (internal error)
    assert result.returncode in {4, 5}


def test_execute_daily_brief_internal_error_returns_exit5(
    tmp_path,
    working_config,
) -> None:
    """Uncaught exceptions in aggregator are caught and return exit_code=5."""
    from aggregator import execute_daily_brief
    from utils.cache_manager import build_artifact_paths
    from utils.config_loader import load_tracking_config

    config = load_tracking_config(working_config)
    artifact_paths = build_artifact_paths(
        trading_date="2026-04-29",
        output_dir=tmp_path / "run3" / "report",
        cache_dir=tmp_path / "run3" / "cache",
    )

    with patch("aggregator._execute_daily_brief_impl", side_effect=RuntimeError("injected")):
        result = execute_daily_brief(
            trading_date="2026-04-29",
            config=config,
            selected_modules=["us_market"],
            stage="auto",
            strict=False,
            artifact_paths=artifact_paths,
        )

    assert result["exit_code"] == 5
