from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from models import MODULE_ORDER
from models import TrackingConfig
from models import TrackingItem
from models import now_iso
from utils.platform_compat import resolve_path


TRACKING_CATEGORY_TO_ITEM_TYPE = {
    "social_accounts": "social_account",
    "research_institutions": "research_institution",
    "commodities": "commodity",
}

MODULE_TO_TRACKING_CATEGORY = {
    "social_consensus": "social_accounts",
    "research_reports": "research_institutions",
    "commodities": "commodities",
}

# FR-025: canonical placeholder tokens (case-insensitive substring check)
_PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {"placeholder", "example", "todo", "xxx", "示例", "占位", "待填"}
)


class ConfigValidationError(ValueError):
    pass


def _has_placeholder(value: str) -> bool:
    """Return True if *value* contains any canonical placeholder token (case-insensitive)."""
    lower = value.lower()
    return any(token in lower for token in _PLACEHOLDER_TOKENS)


def _read_yaml(path_value: Path) -> dict[str, Any]:
    if not path_value.exists():
        raise ConfigValidationError(f"Config file does not exist: {path_value}")
    raw = yaml.safe_load(path_value.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigValidationError(f"Config file must contain a mapping: {path_value}")
    return raw


def _normalize_tracking_items(category: str, raw_items: Any) -> list[TrackingItem]:
    if raw_items is None:
        raise ConfigValidationError(f"Tracking list `{category}` is missing")
    if not isinstance(raw_items, list):
        raise ConfigValidationError(f"Tracking list `{category}` must be a list")

    normalized: list[TrackingItem] = []
    seen_item_ids: set[str] = set()
    item_type = TRACKING_CATEGORY_TO_ITEM_TYPE[category]
    required_fields = {"item_id", "display_name", "source_locator"}

    for index, entry in enumerate(raw_items, start=1):
        if not isinstance(entry, dict):
            raise ConfigValidationError(f"{category}[{index}] must be a mapping")
        missing_fields = required_fields.difference(entry)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ConfigValidationError(f"{category}[{index}] is missing fields: {missing}")

        item_id = str(entry["item_id"])
        if item_id in seen_item_ids:
            raise ConfigValidationError(f"Duplicate item_id `{item_id}` in `{category}`")
        seen_item_ids.add(item_id)

        priority = str(entry.get("priority", "core"))
        if priority not in {"core", "extended"}:
            raise ConfigValidationError(f"Unsupported priority `{priority}` in `{category}`")

        enabled = bool(entry.get("enabled", True))
        disabled_reason = str(entry["disabled_reason"]).strip() if entry.get("disabled_reason") else None

        # FR-029: disabled items must carry a disabled_reason
        if not enabled and not disabled_reason:
            raise ConfigValidationError(
                f"{category}[{index}] has `enabled: false` but is missing `disabled_reason`"
            )

        # FR-025: reject placeholder tokens in display_name and source_locator
        display_name_val = str(entry["display_name"])
        source_locator_val = str(entry["source_locator"])
        if _has_placeholder(display_name_val):
            raise ConfigValidationError(
                f"{category}[{index}] `display_name` contains a placeholder token: {display_name_val!r}"
            )
        if _has_placeholder(source_locator_val):
            raise ConfigValidationError(
                f"{category}[{index}] `source_locator` contains a placeholder token: {source_locator_val!r}"
            )

        metadata = {
            key: value
            for key, value in entry.items()
            if key
            not in {
                "item_id",
                "item_type",
                "display_name",
                "enabled",
                "disabled_reason",
                "priority",
                "source_locator",
                "region",
                "tags",
            }
        }

        normalized.append(
            TrackingItem(
                item_id=item_id,
                item_type=str(entry.get("item_type", item_type)),
                display_name=display_name_val,
                enabled=enabled,
                priority=priority,
                source_locator=source_locator_val,
                region=str(entry["region"]) if entry.get("region") else None,
                tags=[str(tag) for tag in entry.get("tags", [])],
                metadata=metadata,
                disabled_reason=disabled_reason,
            )
        )

    return normalized


def build_config_snapshot(config: TrackingConfig) -> dict[str, Any]:
    snapshot = {
        "version": config.version,
        "updated_at": config.updated_at,
        "critical_modules": config.critical_modules,
        "time_windows": config.time_windows,
        "enable_exploration_sources": config.enable_exploration_sources,
        "module_enabled": config.module_enabled,
        "source_tiers": config.source_tiers,
        "social_accounts": [item.to_dict() for item in config.social_accounts],
        "research_institutions": [item.to_dict() for item in config.research_institutions],
        "commodities": [item.to_dict() for item in config.commodities],
    }
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    snapshot["config_version"] = hashlib.sha256(encoded).hexdigest()[:12]
    return snapshot


def diff_config_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    def _item_map(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {str(item["item_id"]): item for item in items}

    result: dict[str, Any] = {
        "version_changed": before.get("config_version") != after.get("config_version"),
        "module_enabled_changes": {},
        "tracking_changes": {},
    }

    before_modules = before.get("module_enabled", {})
    after_modules = after.get("module_enabled", {})
    for module in MODULE_ORDER:
        if before_modules.get(module) != after_modules.get(module):
            result["module_enabled_changes"][module] = {
                "before": before_modules.get(module),
                "after": after_modules.get(module),
            }

    for category in TRACKING_CATEGORY_TO_ITEM_TYPE:
        before_map = _item_map(before.get(category, []))
        after_map = _item_map(after.get(category, []))
        before_ids = set(before_map)
        after_ids = set(after_map)
        common_ids = sorted(before_ids & after_ids)
        toggled = [
            item_id
            for item_id in common_ids
            if before_map[item_id].get("enabled") != after_map[item_id].get("enabled")
            or before_map[item_id].get("priority") != after_map[item_id].get("priority")
        ]
        result["tracking_changes"][category] = {
            "added": sorted(after_ids - before_ids),
            "removed": sorted(before_ids - after_ids),
            "toggled": toggled,
        }

    return result


def load_tracking_config(config_path: str | Path) -> TrackingConfig:
    config_file = resolve_path(config_path)
    raw_config = _read_yaml(config_file)

    tracking_lists_value = raw_config.get("tracking_lists_path")
    if not tracking_lists_value:
        raise ConfigValidationError("`tracking_lists_path` is required in the main config")

    tracking_file = resolve_path(tracking_lists_value, config_file.parent)
    raw_tracking = _read_yaml(tracking_file)

    modules_raw = raw_config.get("modules") or {}
    if not isinstance(modules_raw, dict):
        raise ConfigValidationError("`modules` must be a mapping")

    module_enabled: dict[str, bool] = {}
    source_tiers: dict[str, str] = {}
    for module in MODULE_ORDER:
        module_config = modules_raw.get(module, {})
        if not isinstance(module_config, dict):
            raise ConfigValidationError(f"Module config for `{module}` must be a mapping")
        module_enabled[module] = bool(module_config.get("enabled", True))
        source_tier = str(module_config.get("source_tier", "production"))
        if source_tier not in {"production", "exploration"}:
            raise ConfigValidationError(f"Unsupported source tier `{source_tier}` for module `{module}`")
        source_tiers[module] = source_tier

    critical_modules = raw_config.get("critical_modules") or []
    if not isinstance(critical_modules, list) or not critical_modules:
        raise ConfigValidationError("`critical_modules` must be a non-empty list")
    for module in critical_modules:
        if module not in MODULE_ORDER:
            raise ConfigValidationError(f"Unknown critical module `{module}`")
        if not module_enabled.get(module, False):
            raise ConfigValidationError(f"Critical module `{module}` cannot be disabled")

    time_windows = raw_config.get("time_windows") or {}
    if not isinstance(time_windows, dict):
        raise ConfigValidationError("`time_windows` must be a mapping")
    for module in MODULE_ORDER:
        window = time_windows.get(module)
        if not isinstance(window, dict) or not str(window.get("label", "")).strip():
            raise ConfigValidationError(f"Module `{module}` requires a non-empty time window label")

    social_accounts = _normalize_tracking_items("social_accounts", raw_tracking.get("social_accounts"))
    research_institutions = _normalize_tracking_items("research_institutions", raw_tracking.get("research_institutions"))
    commodities = _normalize_tracking_items("commodities", raw_tracking.get("commodities"))

    config = TrackingConfig(
        version=str(raw_config.get("version") or raw_tracking.get("version") or "pending-version"),
        updated_at=str(raw_config.get("updated_at") or raw_tracking.get("updated_at") or now_iso()),
        critical_modules=[str(module) for module in critical_modules],
        time_windows=time_windows,
        enable_exploration_sources=bool(raw_config.get("enable_exploration_sources", False)),
        social_accounts=social_accounts,
        research_institutions=research_institutions,
        commodities=commodities,
        module_enabled=module_enabled,
        source_tiers=source_tiers,
        tracking_lists_path=str(tracking_file),
        artifact_defaults={str(key): str(value) for key, value in (raw_config.get("artifact_defaults") or {}).items()},
    )

    for module, category in MODULE_TO_TRACKING_CATEGORY.items():
        if not module_enabled.get(module, False):
            continue
        category_items: list[TrackingItem] = getattr(config, category)
        enabled_core_items = [item for item in category_items if item.enabled and item.priority == "core"]
        if not enabled_core_items:
            raise ConfigValidationError(
                f"`{category}` requires at least one enabled core item when `{module}` is enabled"
            )

    snapshot = build_config_snapshot(config)
    config.snapshot_version = str(snapshot["config_version"])
    return config


def select_modules(config: TrackingConfig, requested_modules: list[str] | None = None) -> list[str]:
    if requested_modules:
        invalid_modules = sorted(set(requested_modules).difference(MODULE_ORDER))
        if invalid_modules:
            raise ConfigValidationError(f"Unknown modules requested: {', '.join(invalid_modules)}")
        disabled = [module for module in requested_modules if not config.module_enabled.get(module, False)]
        if disabled:
            raise ConfigValidationError(f"Requested modules are disabled in config: {', '.join(disabled)}")
        return requested_modules
    return [module for module in MODULE_ORDER if config.module_enabled.get(module, False)]


def tracking_items_for_module(config: TrackingConfig, module: str) -> list[TrackingItem]:
    category = MODULE_TO_TRACKING_CATEGORY.get(module)
    if not category:
        return []
    return list(getattr(config, category))