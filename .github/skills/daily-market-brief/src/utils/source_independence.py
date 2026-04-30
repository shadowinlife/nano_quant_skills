"""Source independence checker (FR-026, T066).

Checks that when multiple modules share the same declared source ID, the
overlap is expected (i.e. explicitly registered as a shared fallback).
"""
from __future__ import annotations

from typing import Any


# Pairs of (primary_module, fallback_module, shared_source_id) that are
# explicitly permitted to share a source by design.
_ALLOWED_SHARED_SOURCES: list[tuple[str, str, str]] = [
    ("us_market", "media_mainline", "us-market-rss"),
    ("media_mainline", "us_market", "media-mainline-rss"),
]


def check_source_independence(
    module_entries: list[dict[str, Any]],
) -> list[str]:
    """Return a list of violation messages for unexpected shared sources.

    *module_entries* is a list of dicts with at least::

        {"module": str, "declared_sources": [str, ...]}

    Returns an empty list when all source assignments are independent or
    are covered by the allowed-shared-source registry.
    """
    # Build map: source_id -> list of modules that declare it
    source_to_modules: dict[str, list[str]] = {}
    for entry in module_entries:
        module = str(entry.get("module", ""))
        for src_id in entry.get("declared_sources", []):
            source_to_modules.setdefault(src_id, []).append(module)

    violations: list[str] = []
    for src_id, modules in source_to_modules.items():
        if len(modules) < 2:
            continue
        for i, mod_a in enumerate(modules):
            for mod_b in modules[i + 1 :]:
                allowed = (
                    (mod_a, mod_b, src_id) in _ALLOWED_SHARED_SOURCES
                    or (mod_b, mod_a, src_id) in _ALLOWED_SHARED_SOURCES
                )
                if not allowed:
                    violations.append(
                        f"Source `{src_id}` is shared by modules `{mod_a}` and `{mod_b}` "
                        f"without an explicit independence exception"
                    )
    return violations
