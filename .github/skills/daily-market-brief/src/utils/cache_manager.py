from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .platform_compat import ensure_directory
from .platform_compat import normalize_path_for_report
from .platform_compat import resolve_path
from .platform_compat import skill_root


@dataclass(slots=True)
class ArtifactPaths:
    run_root: Path
    module_results_dir: Path
    report_dir: Path
    cache_dir: Path


def build_artifact_paths(
    trading_date: str,
    output_dir: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> ArtifactPaths:
    if output_dir:
        report_dir = ensure_directory(resolve_path(output_dir))
        run_root = report_dir.parent
    else:
        run_root = ensure_directory(skill_root() / "tmp" / trading_date)
        report_dir = ensure_directory(run_root / "report")
    module_results_dir = ensure_directory(run_root / "module-results")
    resolved_cache_dir = ensure_directory(resolve_path(cache_dir)) if cache_dir else ensure_directory(run_root / "cache")
    return ArtifactPaths(
        run_root=run_root,
        module_results_dir=module_results_dir,
        report_dir=report_dir,
        cache_dir=resolved_cache_dir,
    )


def read_json(path_value: str | Path, default: Any | None = None) -> Any:
    path = Path(path_value).resolve()
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path_value: str | Path, payload: Any) -> Path:
    path = Path(path_value).resolve()
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_markdown(path_value: str | Path, content: str) -> Path:
    path = Path(path_value).resolve()
    ensure_directory(path.parent)
    path.write_text(content, encoding="utf-8")
    return path


def persist_module_result(module_result: dict[str, Any], paths: ArtifactPaths) -> Path:
    module_name = module_result["module"]
    stage = module_result["stage"]
    return write_json(paths.module_results_dir / f"{module_name}.{stage}.json", module_result)


def report_output_paths(paths: ArtifactPaths, stage: str) -> tuple[Path, Path]:
    return (
        paths.report_dir / f"report.{stage}.json",
        paths.report_dir / f"report.{stage}.md",
    )


def normalize_artifact_path(path_value: str | Path) -> str:
    return normalize_path_for_report(path_value)