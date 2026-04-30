from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models import now_iso


def _build_module_entry(
    module: str,
    final_status: str,
    declared_sources: list[str],
    attempted_sources: list[dict[str, Any]],
    declared_semantic_tag: dict[str, Any] | None = None,
    semantic_drift: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "module": module,
        "declared_semantic_tag": declared_semantic_tag or {},
        "declared_sources": declared_sources,
        "attempted_sources": attempted_sources,
        "final_status": final_status,
    }
    if semantic_drift is not None:
        entry["semantic_drift"] = semantic_drift
    return entry


def write_run_summary(
    run_id: str,
    trade_date: str,
    preflight_ok: bool,
    preflight_missing: list[str],
    module_entries: list[dict[str, Any]],
    output_dir: str | Path,
    coverage_summary: dict[str, int] | None = None,
) -> Path:
    """Write run-summary.json to *output_dir*/<trade_date>/run-summary.json.

    Returns the path to the written file.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "run_id": run_id,
        "generated_at": now_iso(),
        "preflight": {
            "ok": preflight_ok,
            "missing": preflight_missing,
        },
        "modules": module_entries,
    }
    if coverage_summary is not None:
        summary["coverage_summary"] = coverage_summary

    dest = out_dir / "run-summary.json"
    dest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest
