from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_MARKERS = (".git", ".specify")


@dataclass(slots=True)
class PlatformInfo:
    system: str
    release: str
    python: str
    is_windows: bool
    is_macos: bool
    is_linux: bool


def detect_platform() -> PlatformInfo:
    system = platform.system().lower()
    return PlatformInfo(
        system=system,
        release=platform.release(),
        python=sys.version.split()[0],
        is_windows=system == "windows",
        is_macos=system == "darwin",
        is_linux=system == "linux",
    )


def project_root(start: str | Path | None = None) -> Path:
    current = Path(start or __file__).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if any((candidate / marker).exists() for marker in REPO_MARKERS):
            return candidate
    raise FileNotFoundError("Unable to locate repository root from current path")


def skill_root() -> Path:
    return project_root() / ".github" / "skills" / "daily-market-brief"


def resolve_path(path_value: str | Path, base: str | Path | None = None) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    root = Path(base).expanduser().resolve() if base else Path.cwd().resolve()
    return (root / candidate).resolve()


def ensure_directory(path_value: str | Path) -> Path:
    directory = Path(path_value).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def run_subprocess(
    command: list[str],
    cwd: str | Path | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=Path(cwd).resolve() if cwd else None,
        capture_output=True,
        text=True,
        check=check,
    )


def normalize_path_for_report(path_value: str | Path) -> str:
    try:
        return str(Path(path_value).resolve().relative_to(project_root()))
    except ValueError:
        return str(Path(path_value).resolve())