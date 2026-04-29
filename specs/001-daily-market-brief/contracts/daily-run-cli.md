# CLI Contract: Daily Market Brief

## Command Shape

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date YYYY-MM-DD \
  --config PATH \
  [--stage auto|temp|final] \
  [--modules us_market,media_mainline,...] \
  [--output-dir PATH] \
  [--cache-dir PATH]
```

## Required Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--date` | string | Trading date in `YYYY-MM-DD` format |
| `--config` | path | Path to the YAML config file |

## Optional Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--stage` | enum | `auto` | `auto` publishes temp then final when possible; `temp` stops after temp output; `final` waits for final output only |
| `--modules` | csv string | all enabled modules | Restrict execution to a subset of modules |
| `--output-dir` | path | `.github/skills/daily-market-brief/tmp/<trade-date>/report/` | Override report output location |
| `--cache-dir` | path | `.github/skills/daily-market-brief/tmp/<trade-date>/cache/` | Override cache location |
| `--strict` | flag | off | If enabled, missing noncritical modules fail the command instead of returning a partial success |

## Deterministic Behavior

- Config validation happens before any network fetch.
- The config snapshot version is persisted into every run artifact.
- Module execution order is deterministic: `us_market`, `media_mainline`, `social_consensus`, `research_reports`, `commodities` unless `--modules` overrides the set.
- Temp publication is allowed once all critical modules succeed and a report artifact can be produced.
- Formal output uses only production-tier sources unless the config explicitly enables exploration sources.

## Output Artifacts

| Artifact | Location | Notes |
|----------|----------|-------|
| Module JSON results | `.github/skills/daily-market-brief/tmp/<trade-date>/module-results/*.json` | One file per module |
| Aggregated JSON report | `.github/skills/daily-market-brief/tmp/<trade-date>/report/report.<stage>.json` | Conforms to `aggregated-report.schema.json` |
| Markdown report | `.github/skills/daily-market-brief/tmp/<trade-date>/report/report.<stage>.md` | Human-readable standalone report |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | A report artifact was produced successfully, including partial reports with explicit missing markers |
| `2` | Config validation failed or required core tracking lists are empty |
| `3` | Critical modules failed, so no publishable report could be generated |
| `4` | Unexpected internal error prevented execution |

## Success Semantics

- Exit code `0` is valid when noncritical modules are `missing`, `skipped`, or `review_required`, as long as the report clearly marks those states.
- Exit code `0` is not valid if no report artifact exists.
- Under `--strict`, any enabled module failure escalates to a nonzero exit.