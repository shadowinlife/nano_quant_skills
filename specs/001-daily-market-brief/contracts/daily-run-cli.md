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
| `4` | Preflight self-check failed (missing runtime dependency or required configuration). stderr line 1 MUST start with the literal prefix `PREFLIGHT_FAIL:` followed by a comma-separated list of missing items |
| `5` | Unexpected internal error prevented execution (reserved for uncaught exceptions outside preflight scope) |

Exit codes 3 and 4 are strictly mutually exclusive: preflight runs before any module execution and short-circuits with code 4 when it fails. A run that reaches module execution can only return 0 / 3 / 5 (and 2 if config validation reuses preflight integration).

### `--skip-preflight`

`--skip-preflight` is a local debugging escape hatch that disables FR-021 self-check. It MUST NOT be used in CI or scheduled runs; the CLI MUST emit a stderr warning when this flag is set.

## Success Semantics

- Exit code `0` is valid when noncritical modules are `missing`, `skipped`, or `review_required`, as long as the report clearly marks those states.
- Exit code `0` is not valid if no report artifact exists.
- Under `--strict`, any enabled module failure escalates to a nonzero exit.
- A successful run MUST also write `tmp/<trade-date>/run-summary.json` and reference it from the aggregated report JSON via the `run_summary_path` field.