from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from utils import ConfigValidationError
from utils import build_artifact_paths
from utils import get_logger
from utils import load_tracking_config
from utils import select_modules


LOGGER = get_logger("daily-market-brief.cli")


def parse_trading_date(raw_date: str) -> str:
    try:
        return date.fromisoformat(raw_date).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Trading date must be in YYYY-MM-DD format") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an A-share pre-open daily market brief.",
    )
    parser.add_argument(
        "--date",
        required=True,
        type=parse_trading_date,
        help="Trading date in YYYY-MM-DD format",
    )
    parser.add_argument("--config", required=True, help="Path to the YAML config file")
    parser.add_argument(
        "--stage",
        choices=["auto", "temp", "final"],
        default="auto",
        help="auto publishes temp then final when possible; temp stops after temp output; final waits for final output only",
    )
    parser.add_argument(
        "--modules",
        help="Comma separated module list. Defaults to all enabled modules.",
    )
    parser.add_argument(
        "--output-dir",
        help="Override report output directory. Defaults to tmp/<trade-date>/report/.",
    )
    parser.add_argument(
        "--cache-dir",
        help="Override cache directory. Defaults to tmp/<trade-date>/cache/.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any enabled module failure instead of returning partial success.",
    )
    return parser


def parse_modules_arg(raw_modules: str | None) -> list[str] | None:
    if not raw_modules:
        return None
    modules = [module.strip() for module in raw_modules.split(",") if module.strip()]
    return modules or None


def _load_orchestrator():
    try:
        from aggregator import execute_daily_brief
    except ImportError as exc:
        raise RuntimeError("Workflow orchestrator is not ready yet") from exc
    return execute_daily_brief


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_tracking_config(args.config)
        selected_modules = select_modules(config, parse_modules_arg(args.modules))
        paths = build_artifact_paths(args.date, output_dir=args.output_dir, cache_dir=args.cache_dir)
        execute_daily_brief = _load_orchestrator()
        result = execute_daily_brief(
            trading_date=args.date,
            config=config,
            selected_modules=selected_modules,
            stage=args.stage,
            strict=args.strict,
            artifact_paths=paths,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return int(result.get("exit_code", 0))
    except ConfigValidationError as exc:
        LOGGER.error(str(exc))
        parser.exit(2, f"Config validation failed: {exc}\n")
    except RuntimeError as exc:
        LOGGER.error(str(exc))
        parser.exit(4, f"Internal error: {exc}\n")
    except Exception as exc:
        LOGGER.error(str(exc))
        parser.exit(4, f"Unexpected error: {exc}\n")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())