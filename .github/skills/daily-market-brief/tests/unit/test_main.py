from __future__ import annotations

import pytest

from main import build_parser


def test_cli_rejects_invalid_trading_date() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--date", "not-a-date", "--config", "config/config.example.yaml"])

    assert exc_info.value.code == 2


def test_cli_normalizes_valid_trading_date() -> None:
    parser = build_parser()

    args = parser.parse_args(["--date", "2026-04-29", "--config", "config/config.example.yaml"])

    assert args.date == "2026-04-29"