#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v conda >/dev/null 2>&1; then
  conda run -n legonanobot python "$ROOT_DIR/src/validate_daily_run.py"
else
  python3 "$ROOT_DIR/src/validate_daily_run.py"
fi