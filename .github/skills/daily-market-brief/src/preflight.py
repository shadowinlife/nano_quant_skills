from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_REQUIRED_DEPS: list[str] = [
    "yaml",
    "feedparser",
    "jsonschema",
    "requests",
]


@dataclass(slots=True)
class PreflightResult:
    ok: bool
    missing: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "missing": self.missing}

    def stderr_line(self) -> str | None:
        """Return a PREFLIGHT_FAIL line for stderr, or None when ok."""
        if self.ok:
            return None
        return f"PREFLIGHT_FAIL: {', '.join(self.missing)}"


def check_deps(extra: list[str] | None = None) -> list[str]:
    """Return the names of importable packages that cannot be imported."""
    missing: list[str] = []
    for pkg in [*_REQUIRED_DEPS, *(extra or [])]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def check_config_file(config_path: str | Path) -> list[str]:
    """Return validation issues for the config file, empty list when OK."""
    issues: list[str] = []
    config_file = Path(config_path)
    if not config_file.exists():
        issues.append(f"config_file_missing:{config_file}")
    elif not config_file.is_file():
        issues.append(f"config_path_not_file:{config_file}")
    return issues


def run_preflight(
    config_path: str | Path | None = None,
    extra_deps: list[str] | None = None,
) -> PreflightResult:
    """Run all preflight checks and return a PreflightResult.

    Checks performed:
    1. Required Python packages can be imported.
    2. Config file exists (if *config_path* supplied).
    """
    missing: list[str] = []
    missing.extend(check_deps(extra_deps))
    if config_path is not None:
        missing.extend(check_config_file(config_path))
    return PreflightResult(ok=len(missing) == 0, missing=missing)
