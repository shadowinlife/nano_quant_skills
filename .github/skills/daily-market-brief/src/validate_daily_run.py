from __future__ import annotations

import json
import sys
from pathlib import Path

from utils import ConfigValidationError
from utils import build_artifact_paths
from utils import get_logger
from utils import load_tracking_config
from utils.platform_compat import detect_platform
from utils.platform_compat import run_subprocess
from utils.platform_compat import skill_root


LOGGER = get_logger("daily-market-brief.validate")


def validate_environment() -> dict[str, object]:
    platform_info = detect_platform()
    return {
        "system": platform_info.system,
        "release": platform_info.release,
        "python": platform_info.python,
    }


def validate_cli_help(skill_dir: Path) -> None:
    result = run_subprocess(
        [sys.executable, str(skill_dir / "src" / "main.py"), "--help"],
        cwd=skill_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "CLI help command failed")


def validate_artifact_dirs(skill_dir: Path) -> dict[str, str]:
    paths = build_artifact_paths("validation-smoke")
    return {
        "run_root": str(paths.run_root),
        "module_results_dir": str(paths.module_results_dir),
        "report_dir": str(paths.report_dir),
        "cache_dir": str(paths.cache_dir),
    }


def main() -> int:
    skill_dir = skill_root()
    config_path = skill_dir / "config" / "config.example.yaml"
    payload: dict[str, object] = {}
    try:
        payload["environment"] = validate_environment()
        payload["config_version"] = load_tracking_config(config_path).snapshot_version
        validate_cli_help(skill_dir)
        payload["artifact_dirs"] = validate_artifact_dirs(skill_dir)
        payload["status"] = "ok"
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0
    except ConfigValidationError as exc:
        LOGGER.error(str(exc))
        sys.stderr.write(f"Config validation failed: {exc}\n")
        return 2
    except Exception as exc:
        LOGGER.error(str(exc))
        sys.stderr.write(f"Validation failed: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())