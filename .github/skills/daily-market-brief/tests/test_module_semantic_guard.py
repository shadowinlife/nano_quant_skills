"""Unit tests for module semantic guard / semantic drift detection (T060, FR-023)."""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from modules.common import MODULE_DECLARED_SEMANTIC_TAGS, detect_semantic_drift


def test_no_drift_when_identical():
    tag = {"language": "zh", "region": "cn", "media_type": "newswire"}
    assert detect_semantic_drift(tag, tag) is None


def test_language_drift_detected():
    declared = {"language": "en", "region": "us", "media_type": "newswire"}
    observed = {"language": "zh", "region": "us", "media_type": "newswire"}
    drift = detect_semantic_drift(declared, observed)
    assert drift is not None
    assert "language" in drift["drift_categories"]
    assert "region" not in drift["drift_categories"]


def test_multi_dim_drift():
    declared = {"language": "en", "region": "us", "media_type": "newswire"}
    observed = {"language": "zh", "region": "cn", "media_type": "social"}
    drift = detect_semantic_drift(declared, observed)
    assert drift is not None
    assert set(drift["drift_categories"]) == {"language", "region", "media_type"}


def test_drift_none_when_declared_missing():
    assert detect_semantic_drift(None, {"language": "zh"}) is None


def test_drift_none_when_observed_missing():
    assert detect_semantic_drift({"language": "en"}, None) is None


def test_all_modules_have_declared_tags():
    from models import MODULE_ORDER
    for module in MODULE_ORDER:
        assert module in MODULE_DECLARED_SEMANTIC_TAGS, f"Module {module} missing declared semantic tag"


def test_build_module_result_populates_semantic_drift():
    from models import TrackingItem
    from modules.common import build_module_result

    payload = {
        "records": [],
        "source_state": "ok",
        "note": "test",
        # Observed tag with language drift from declared "en"
        "semantic_tag": {"language": "zh", "region": "us", "media_type": "newswire"},
    }
    result = build_module_result(
        run_id="r1",
        module="us_market",
        stage="final",
        time_window={"label": "近一交易日"},
        source_payload=payload,
    )
    assert result.semantic_drift is not None
    assert "language" in result.semantic_drift["drift_categories"]


def test_build_module_result_no_drift_when_no_observed_tag():
    from modules.common import build_module_result

    payload = {"records": [], "source_state": "ok", "note": ""}
    result = build_module_result(
        run_id="r1",
        module="media_mainline",
        stage="final",
        time_window={"label": "近一交易日"},
        source_payload=payload,
    )
    assert result.semantic_drift is None
