"""Unit tests for tracking placeholder guard and disabled_reason (T065, FR-025, FR-029)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

SKILL_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = SKILL_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from utils.config_loader import ConfigValidationError, _has_placeholder, _normalize_tracking_items


def test_has_placeholder_tokens():
    assert _has_placeholder("placeholder account")
    assert _has_placeholder("TODO")
    assert _has_placeholder("xxx")
    assert _has_placeholder("示例用户")
    assert _has_placeholder("占位账号")
    assert _has_placeholder("待填内容")
    assert _has_placeholder("example feed")


def test_no_placeholder_in_normal_value():
    assert not _has_placeholder("雪球热帖")
    assert not _has_placeholder("wind.com/feed")
    assert not _has_placeholder("bloomberg-rss")


def test_normalize_items_rejects_placeholder_display_name():
    items = [
        {
            "item_id": "acc-001",
            "display_name": "placeholder账号",
            "source_locator": "https://real.example/feed",
        }
    ]
    with pytest.raises(ConfigValidationError, match="placeholder token"):
        _normalize_tracking_items("social_accounts", items)


def test_normalize_items_rejects_placeholder_source_locator():
    items = [
        {
            "item_id": "acc-001",
            "display_name": "雪球热帖",
            "source_locator": "https://todo.example/feed",
        }
    ]
    with pytest.raises(ConfigValidationError, match="placeholder token"):
        _normalize_tracking_items("social_accounts", items)


def test_normalize_items_disabled_requires_reason():
    items = [
        {
            "item_id": "acc-001",
            "display_name": "雪球热帖",
            "source_locator": "https://real.example/feed",
            "enabled": False,
        }
    ]
    with pytest.raises(ConfigValidationError, match="disabled_reason"):
        _normalize_tracking_items("social_accounts", items)


def test_normalize_items_disabled_with_reason_accepted():
    items = [
        {
            "item_id": "acc-001",
            "display_name": "雪球热帖",
            "source_locator": "https://feeds.stub.local/hot",
            "enabled": False,
            "disabled_reason": "源站已下线，等待替换",
        }
    ]
    result = _normalize_tracking_items("social_accounts", items)
    assert len(result) == 1
    assert result[0].disabled_reason == "源站已下线，等待替换"
    assert result[0].enabled is False


def test_normalize_enabled_item_does_not_need_reason():
    items = [
        {
            "item_id": "acc-001",
            "display_name": "雪球热帖",
            "source_locator": "https://feeds.stub.local/hot",
        }
    ]
    result = _normalize_tracking_items("social_accounts", items)
    assert result[0].disabled_reason is None


def test_all_placeholder_tokens_case_insensitive():
    tokens = ["PLACEHOLDER", "Example", "TODO", "XXX", "示例", "占位", "待填"]
    for tok in tokens:
        assert _has_placeholder(tok), f"Expected {tok!r} to be detected as placeholder"


def test_normalize_items_with_full_config(tmp_path, working_config):
    """Smoke test: full tracking-lists.yaml passes placeholder guard."""
    from utils.config_loader import load_tracking_config
    # Should not raise
    load_tracking_config(str(working_config))
