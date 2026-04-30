"""Unit tests for failure_taxonomy.py (T055)."""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from failure_taxonomy import FailureClass


def test_failure_class_enum_values():
    values = {fc.value for fc in FailureClass}
    assert values == {
        "dependency_missing",
        "network_timeout",
        "http_non_2xx",
        "parse_empty",
        "source_schema_changed",
        "unknown",
    }


def test_from_exception_import_error():
    exc = ImportError("No module named 'akshare'")
    assert FailureClass.from_exception(exc) == FailureClass.DEPENDENCY_MISSING


def test_from_exception_timeout():
    exc = TimeoutError("connection timed out")
    assert FailureClass.from_exception(exc) == FailureClass.NETWORK_TIMEOUT


def test_from_exception_msg_timeout():
    exc = ConnectionError("socket timeout occurred")
    assert FailureClass.from_exception(exc) == FailureClass.NETWORK_TIMEOUT


def test_from_exception_generic():
    exc = RuntimeError("some unexpected error")
    assert FailureClass.from_exception(exc) == FailureClass.UNKNOWN


def test_from_exception_parse():
    exc = ValueError("parse error: unexpected field foo")
    assert FailureClass.from_exception(exc) == FailureClass.SOURCE_SCHEMA_CHANGED


def test_failure_class_is_string():
    assert FailureClass.UNKNOWN == "unknown"
    assert isinstance(FailureClass.DEPENDENCY_MISSING, str)
