# Quickstart: A股开盘核心新闻聚合研究 Skill

## Goal

Provide the minimum local path to install, validate, and run the planned daily brief workflow after implementation lands.

## Prerequisites

- Conda is installed locally.
- The `legonanobot` environment exists and is the default execution environment for this repository.
- Any production source credentials are supplied via environment variables at runtime, not committed to the repository.

## Setup

macOS/Linux:

```bash
conda activate legonanobot
pip install -r .github/skills/daily-market-brief/requirements.txt
cp .github/skills/daily-market-brief/config/config.example.yaml \
  .github/skills/daily-market-brief/config/local.yaml
```

Windows PowerShell:

```powershell
conda activate legonanobot
pip install -r .github/skills/daily-market-brief/requirements.txt
Copy-Item .github/skills/daily-market-brief/config/config.example.yaml .github/skills/daily-market-brief/config/local.yaml
```

If `tushare` is enabled for any configured module, export `TUSHARE_TOKEN` only in the current shell session before running the workflow.

## Minimal Configuration

Edit `.github/skills/daily-market-brief/config/local.yaml` and confirm:

- `critical_modules` contains `us_market` and `media_mainline`.
- Core tracking lists are populated for social accounts, research institutions, and commodities.
- `enable_exploration_sources` remains `false` for MVP.

## Validation Commands

Run these commands before commit:

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py --help
pytest .github/skills/daily-market-brief/tests/ -v
conda run -n legonanobot python .github/skills/daily-market-brief/src/validate_daily_run.py
```

On macOS/Linux, you may also run the POSIX wrapper:

```bash
./.github/skills/daily-market-brief/validate-daily-run.sh
```

On Windows, use the Python validator instead of the shell wrapper.

Record the commands and pass results in `specs/001-daily-market-brief/remediation-log.md`.

## Planned Execution Commands

Automatic stage selection:

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --stage auto
```

Force temporary report only:

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --stage temp
```

Run a subset of modules:

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --modules us_market,media_mainline,commodities
```

## Expected Artifacts

- Intermediate module JSON: `.github/skills/daily-market-brief/tmp/<trade-date>/module-results/*.json`
- Structured aggregated JSON: `.github/skills/daily-market-brief/tmp/<trade-date>/report/report.<stage>.json`
- Markdown report: `.github/skills/daily-market-brief/tmp/<trade-date>/report/report.<stage>.md`

## Pass Criteria

- The CLI help command exits with code `0`.
- The Python validation command exits with code `0` and confirms environment detection, config validation, and artifact path creation.
- On macOS/Linux, the shell wrapper exits with code `0` and delegates to the same validation flow.
- A successful workflow produces at least one Markdown report plus JSON module artifacts.
- A temp report can be emitted when critical modules succeed even if noncritical modules are missing.
- The final report respects the agreed readability limits: at most 5 top highlights, at most 10 sections, and each section summary within 60 Chinese characters.

## Non-Goals for MVP Validation

- A 20-trading-day uptime simulation is not part of the MVP gate.
- Exploration sources are not part of the formal-output pass criteria.
- Operational metrics dashboards are not required before the first end-to-end workflow passes.