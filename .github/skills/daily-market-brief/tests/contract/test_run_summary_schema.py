"""Contract test: validate run-summary.json against run-summary.schema.json (T045)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = SKILL_ROOT / "src"
SPEC_ROOT = Path(__file__).resolve().parents[5] / "specs" / "001-daily-market-brief"
SCHEMA_PATH = SPEC_ROOT / "contracts" / "run-summary.schema.json"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture(scope="module")
def run_summary_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _valid_run_summary() -> dict:
    return {
        "run_id": "2024-01-15:v1",
        "generated_at": "2024-01-15T01:00:00+00:00",
        "preflight": {"ok": True, "missing": []},
        "modules": [
            {
                "module": "us_market",
                "declared_semantic_tag": {
                    "language": "en",
                    "region": "us",
                    "media_type": "newswire",
                },
                "declared_sources": ["us-market-rss"],
                "attempted_sources": [
                    {
                        "url": "us-market-rss",
                        "protocol": "rss",
                        "http_status": None,
                        "records": 3,
                        "fail_class": None,
                    }
                ],
                "final_status": "confirmed",
            }
        ],
    }


def test_valid_run_summary_passes_schema(run_summary_schema):
    from jsonschema import validate

    validate(instance=_valid_run_summary(), schema=run_summary_schema)


def test_missing_run_id_fails_schema(run_summary_schema):
    from jsonschema import ValidationError, validate

    doc = _valid_run_summary()
    del doc["run_id"]
    with pytest.raises(ValidationError):
        validate(instance=doc, schema=run_summary_schema)


def test_missing_preflight_fails_schema(run_summary_schema):
    from jsonschema import ValidationError, validate

    doc = _valid_run_summary()
    del doc["preflight"]
    with pytest.raises(ValidationError):
        validate(instance=doc, schema=run_summary_schema)


def test_preflight_ok_true_with_missing_items_fails_schema(run_summary_schema):
    """When ok=true, missing must be empty per the allOf constraint."""
    from jsonschema import ValidationError, validate

    doc = _valid_run_summary()
    doc["preflight"] = {"ok": True, "missing": ["yaml"]}
    with pytest.raises(ValidationError):
        validate(instance=doc, schema=run_summary_schema)


def test_module_entry_requires_declared_semantic_tag(run_summary_schema):
    from jsonschema import ValidationError, validate

    doc = _valid_run_summary()
    del doc["modules"][0]["declared_semantic_tag"]
    with pytest.raises(ValidationError):
        validate(instance=doc, schema=run_summary_schema)


def test_module_entry_with_semantic_drift_passes(run_summary_schema):
    from jsonschema import validate

    doc = _valid_run_summary()
    doc["modules"][0]["semantic_drift"] = {
        "declared": {"language": "en", "region": "us", "media_type": "newswire"},
        "observed": {"language": "zh", "region": "cn", "media_type": "newswire"},
        "drift_categories": ["language", "region"],
    }
    validate(instance=doc, schema=run_summary_schema)


def test_invalid_module_name_fails_schema(run_summary_schema):
    from jsonschema import ValidationError, validate

    doc = _valid_run_summary()
    doc["modules"][0]["module"] = "not_a_module"
    with pytest.raises(ValidationError):
        validate(instance=doc, schema=run_summary_schema)


def test_invalid_fail_class_fails_schema(run_summary_schema):
    from jsonschema import ValidationError, validate

    doc = _valid_run_summary()
    doc["modules"][0]["attempted_sources"][0]["fail_class"] = "bad_class"
    with pytest.raises(ValidationError):
        validate(instance=doc, schema=run_summary_schema)


def test_write_run_summary_produces_valid_json(tmp_path, run_summary_schema):
    """Integration: write_run_summary() output validates against the schema."""
    from jsonschema import validate
    from run_summary import write_run_summary

    path = write_run_summary(
        run_id="2024-01-15:v1",
        trade_date="2024-01-15",
        preflight_ok=True,
        preflight_missing=[],
        module_entries=[
            {
                "module": "us_market",
                "declared_semantic_tag": {"language": "en", "region": "us", "media_type": "newswire"},
                "declared_sources": ["us-market-rss"],
                "attempted_sources": [
                    {
                        "url": "us-market-rss",
                        "protocol": "rss",
                        "http_status": None,
                        "records": 0,
                        "fail_class": None,
                    }
                ],
                "final_status": "confirmed",
            }
        ],
        output_dir=tmp_path,
    )
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate(instance=doc, schema=run_summary_schema)
