from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb

try:
    from .common import CompanyProfile, detect_company_profile, default_db_path, parse_date, connect_read_only
except ImportError:
    from common import CompanyProfile, detect_company_profile, default_db_path, parse_date, connect_read_only


REPORT_TYPE = "1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _float_or_none(value: Any) -> float | None:
    if _is_missing(value):
        return None
    return float(value)


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _object_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    row = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


# ---------------------------------------------------------------------------
# Employee-count bundle (human-in-loop input)
# ---------------------------------------------------------------------------

def _load_employee_bundle(path: Path | None) -> dict[tuple[str, int], int]:
    """Load user-provided employee counts. Format:

    [
      {"ts_code": "600660.SH", "year": 2025, "employee_count": 33000},
      ...
    ]

    Returns a dict keyed by (ts_code_upper, year) → employee_count.

    Only real headcount values are accepted. Proxy values (e.g. wages / avg-salary)
    MUST NOT be inserted here; if the user does not have real data they should
    leave the bundle empty and accept the ``human-in-loop-required`` status.
    """
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("employee_counts") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError(
            "Employee-count bundle must be a list or an object with an 'employee_counts' field"
        )
    mapping: dict[tuple[str, int], int] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Each employee-count entry must be an object")
        ts_code = str(item.get("ts_code") or "").strip().upper()
        if not ts_code:
            raise ValueError("Each employee-count entry must contain ts_code")
        try:
            year = int(str(item.get("year")).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Each employee-count entry must contain a valid integer year, got: {item.get('year')!r}"
            ) from exc
        count_value = item.get("employee_count")
        if count_value is None:
            raise ValueError("Each employee-count entry must contain employee_count")
        try:
            count = int(count_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"employee_count must be an integer, got: {count_value!r}"
            ) from exc
        if count <= 0:
            raise ValueError(
                f"employee_count must be a positive integer, got: {count}"
            )
        mapping[(ts_code, year)] = count
    return mapping


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _fetch_efficiency_inputs(
    con: duckdb.DuckDBPyConnection,
    stock: str,
    as_of_date: date,
    lookback_years: int,
) -> list[dict[str, Any]]:
    """Fetch balance sheet + income + cashflow fields needed for efficiency metrics."""
    query = f"""
    WITH params AS (
        SELECT
            CAST(? AS VARCHAR)  AS ts_code,
            CAST(? AS DATE)     AS as_of_date,
            CAST(? AS INTEGER)  AS lookback_years
    ),
    balance_yearly AS (
        SELECT
            b.ts_code,
            b.end_date,
            COALESCE(b.f_ann_date, b.ann_date, b.end_date) AS visible_date,
            b.accounts_receiv,
            b.inventories,
            b.prepayment,
            b.acct_payable,
            b.adv_receipts,
            b.contract_liab,
            b.fix_assets,
            b.total_assets
        FROM fin_balance b
        CROSS JOIN params p
        WHERE b.ts_code = p.ts_code
          AND b.report_type = '{REPORT_TYPE}'
          AND EXTRACT(MONTH FROM b.end_date) = 12
          AND EXTRACT(DAY FROM b.end_date) = 31
          AND COALESCE(b.f_ann_date, b.ann_date, b.end_date) <= p.as_of_date
    ),
    income_yearly AS (
        SELECT
            i.ts_code,
            i.end_date,
            COALESCE(i.f_ann_date, i.ann_date, i.end_date) AS visible_date,
            i.revenue,
            i.n_income_attr_p
        FROM fin_income i
        CROSS JOIN params p
        WHERE i.ts_code = p.ts_code
          AND i.report_type = '{REPORT_TYPE}'
          AND EXTRACT(MONTH FROM i.end_date) = 12
          AND EXTRACT(DAY FROM i.end_date) = 31
          AND COALESCE(i.f_ann_date, i.ann_date, i.end_date) <= p.as_of_date
    ),
    cashflow_yearly AS (
        SELECT
            c.ts_code,
            c.end_date,
            COALESCE(c.f_ann_date, c.ann_date, c.end_date) AS visible_date,
            c.c_paid_to_for_empl
        FROM fin_cashflow c
        CROSS JOIN params p
        WHERE c.ts_code = p.ts_code
          AND c.report_type = '{REPORT_TYPE}'
          AND EXTRACT(MONTH FROM c.end_date) = 12
          AND EXTRACT(DAY FROM c.end_date) = 31
          AND COALESCE(c.f_ann_date, c.ann_date, c.end_date) <= p.as_of_date
    ),
    -- Deduplicate balance
    bal_dedup AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY ts_code, end_date ORDER BY visible_date DESC
        ) AS rn FROM balance_yearly
    ),
    inc_dedup AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY ts_code, end_date ORDER BY visible_date DESC
        ) AS rn FROM income_yearly
    ),
    cf_dedup AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY ts_code, end_date ORDER BY visible_date DESC
        ) AS rn FROM cashflow_yearly
    ),
    combined AS (
        SELECT
            b.ts_code,
            b.end_date,
            b.accounts_receiv,
            b.inventories,
            b.prepayment,
            b.acct_payable,
            b.adv_receipts,
            b.contract_liab,
            b.fix_assets,
            b.total_assets,
            i.revenue,
            i.n_income_attr_p,
            c.c_paid_to_for_empl
        FROM bal_dedup b
        LEFT JOIN inc_dedup i  ON b.ts_code = i.ts_code AND b.end_date = i.end_date AND i.rn = 1
        LEFT JOIN cf_dedup  c  ON b.ts_code = c.ts_code AND b.end_date = c.end_date AND c.rn = 1
        WHERE b.rn = 1
    ),
    ranked AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY ts_code ORDER BY end_date DESC
        ) AS rn
        FROM combined
    )
    SELECT
        ts_code, end_date,
        accounts_receiv, inventories, prepayment,
        acct_payable, adv_receipts, contract_liab,
        fix_assets, total_assets,
        revenue, n_income_attr_p, c_paid_to_for_empl
    FROM ranked
    WHERE rn <= (SELECT lookback_years FROM params)
    ORDER BY end_date DESC
    """
    result = con.execute(query, [stock, as_of_date, lookback_years])
    columns = [item[0] for item in result.description]
    return [{col: val for col, val in zip(columns, record)} for record in result.fetchall()]


def _fetch_turnover_indicators(
    con: duckdb.DuckDBPyConnection,
    stock: str,
    as_of_date: date,
    lookback_years: int,
) -> list[dict[str, Any]]:
    """Fetch turnover ratios from fin_indicator."""
    query = f"""
    WITH params AS (
        SELECT
            CAST(? AS VARCHAR)  AS ts_code,
            CAST(? AS DATE)     AS as_of_date,
            CAST(? AS INTEGER)  AS lookback_years
    ),
    indicator_yearly AS (
        SELECT
            fi.ts_code,
            fi.end_date,
            COALESCE(fi.ann_date_key, fi.ann_date, fi.end_date) AS sort_key,
            fi.ar_turn,
            fi.fa_turn,
            fi.assets_turn,
            fi.ca_turn
        FROM fin_indicator fi
        CROSS JOIN params p
        WHERE fi.ts_code = p.ts_code
          AND EXTRACT(MONTH FROM fi.end_date) = 12
          AND EXTRACT(DAY FROM fi.end_date) = 31
          AND COALESCE(fi.ann_date_key, fi.ann_date, fi.end_date) <= p.as_of_date
    ),
    deduped AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY ts_code, end_date ORDER BY sort_key DESC
        ) AS rn
        FROM indicator_yearly
    ),
    ranked AS (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY ts_code ORDER BY end_date DESC
        ) AS rn2
        FROM deduped WHERE rn = 1
    )
    SELECT ts_code, end_date, ar_turn, fa_turn, assets_turn, ca_turn
    FROM ranked
    WHERE rn2 <= (SELECT lookback_years FROM params)
    ORDER BY end_date DESC
    """
    result = con.execute(query, [stock, as_of_date, lookback_years])
    columns = [item[0] for item in result.description]
    return [{col: val for col, val in zip(columns, record)} for record in result.fetchall()]


# ---------------------------------------------------------------------------
# Benchmark: find largest peer by market cap
# ---------------------------------------------------------------------------

def _find_benchmark(
    con: duckdb.DuckDBPyConnection,
    stock: str,
    as_of_date: date,
) -> dict[str, Any] | None:
    """Find the largest non-self peer in SW L3 by total_mv."""
    if not _object_exists(con, "idx_sw_l3_peers") or not _object_exists(con, "stk_factor_pro"):
        return None

    # Get peers
    peers = con.execute(
        """
        SELECT DISTINCT peer_ts_code, peer_name
        FROM idx_sw_l3_peers
        WHERE anchor_ts_code = ?
          AND peer_is_self = false
        """,
        [stock],
    ).fetchall()

    if not peers:
        return None

    peer_codes = [p[0] for p in peers]
    peer_name_map = {p[0]: p[1] for p in peers}

    # Find the latest trade_date <= as_of_date with data in stk_factor_pro
    latest_date_row = con.execute(
        """
        SELECT MAX(trade_date)
        FROM stk_factor_pro
        WHERE trade_date <= CAST(? AS DATE)
          AND total_mv IS NOT NULL
        """,
        [as_of_date],
    ).fetchone()

    if not latest_date_row or latest_date_row[0] is None:
        return None

    latest_trade_date = latest_date_row[0]

    # Build parameterized query for peer market cap lookup
    placeholders = ", ".join(["?"] * len(peer_codes))
    top_row = con.execute(
        f"""
        SELECT ts_code, total_mv
        FROM stk_factor_pro
        WHERE trade_date = ?
          AND ts_code IN ({placeholders})
          AND total_mv IS NOT NULL
        ORDER BY total_mv DESC
        LIMIT 1
        """,
        [latest_trade_date] + peer_codes,
    ).fetchone()

    if not top_row:
        return None

    return {
        "ts_code": top_row[0],
        "name": peer_name_map.get(top_row[0], ""),
        "total_mv": float(top_row[1]),
        "mv_trade_date": latest_trade_date.isoformat() if isinstance(latest_trade_date, date) else str(latest_trade_date),
    }


def _fetch_peer_industry_info(
    con: duckdb.DuckDBPyConnection,
    stock: str,
) -> dict[str, Any]:
    """Get SW L3 industry info for the stock."""
    if not _object_exists(con, "idx_sw_l3_peers"):
        return {}
    row = con.execute(
        """
        SELECT DISTINCT l1_name, l2_name, l3_name, l3_code, peer_group_size
        FROM idx_sw_l3_peers
        WHERE anchor_ts_code = ?
        LIMIT 1
        """,
        [stock],
    ).fetchone()
    if not row:
        return {}
    return {
        "l1_name": row[0],
        "l2_name": row[1],
        "l3_name": row[2],
        "l3_code": row[3],
        "peer_group_size": row[4],
    }


# ---------------------------------------------------------------------------
# Compute efficiency metrics
# ---------------------------------------------------------------------------

def _compute_efficiency(
    rows: list[dict[str, Any]],
    employee_bundle: dict[tuple[str, int], int] | None = None,
    ts_code: str | None = None,
) -> list[dict[str, Any]]:
    """Compute WC/revenue, fix_assets/revenue, labor productivity for each year.

    If ``employee_bundle`` + ``ts_code`` provided, also compute real
    ``revenue_per_employee`` and ``profit_per_employee``. Otherwise the per-capita
    fields are kept ``None`` and the caller must surface the data gap as
    human-in-loop.
    """
    employee_bundle = employee_bundle or {}
    ts_code_key = (ts_code or "").strip().upper()
    results = []
    for row in rows:
        ar = _float_or_none(row.get("accounts_receiv"))
        inv = _float_or_none(row.get("inventories"))
        prep = _float_or_none(row.get("prepayment"))
        ap = _float_or_none(row.get("acct_payable"))
        adv = _float_or_none(row.get("adv_receipts"))
        cl = _float_or_none(row.get("contract_liab"))
        fix = _float_or_none(row.get("fix_assets"))
        rev = _float_or_none(row.get("revenue"))
        profit = _float_or_none(row.get("n_income_attr_p"))
        labor = _float_or_none(row.get("c_paid_to_for_empl"))

        # Working capital
        wc_parts = [ar, inv, prep]
        wc_minus = [ap, adv or 0, cl or 0]
        if all(p is not None for p in wc_parts) and all(p is not None for p in [ap]):
            wc = sum(wc_parts) - sum(wc_minus)
        else:
            wc = None

        wc_per_rev = _safe_div(wc, rev)
        fix_per_rev = _safe_div(fix, rev)
        rev_per_labor = _safe_div(rev, labor)
        profit_per_labor = _safe_div(profit, labor)

        # Real per-capita metrics (only if user provided headcount)
        employee_count: int | None = None
        year_value = None
        end_date_value = row.get("end_date")
        if isinstance(end_date_value, date):
            year_value = end_date_value.year
        elif end_date_value:
            try:
                year_value = int(str(end_date_value)[:4])
            except ValueError:
                year_value = None
        if ts_code_key and year_value is not None:
            employee_count = employee_bundle.get((ts_code_key, year_value))

        revenue_per_employee = _safe_div(rev, employee_count) if employee_count else None
        profit_per_employee = _safe_div(profit, employee_count) if employee_count else None
        avg_labor_cost_per_employee = (
            _safe_div(labor, employee_count) if employee_count else None
        )

        results.append({
            "end_date": row["end_date"],
            "revenue": rev,
            "n_income_attr_p": profit,
            "working_capital": wc,
            "wc_per_revenue": wc_per_rev,
            "fix_assets": fix,
            "fix_assets_per_revenue": fix_per_rev,
            "c_paid_to_for_empl": labor,
            "revenue_per_labor_cost": rev_per_labor,
            "profit_per_labor_cost": profit_per_labor,
            # True per-capita metrics (only populated when the user supplies a
            # verified employee count for that (ts_code, year)).
            "employee_count": employee_count,
            "revenue_per_employee": revenue_per_employee,
            "profit_per_employee": profit_per_employee,
            "avg_labor_cost_per_employee": avg_labor_cost_per_employee,
        })
    return results


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _build_summary(
    eff_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not eff_rows:
        return {
            "years_returned": 0,
            "wc_per_revenue_latest": None,
            "fix_assets_per_revenue_latest": None,
            "revenue_per_labor_cost_latest": None,
            "revenue_per_employee_latest": None,
            "profit_per_employee_latest": None,
            "per_capita_status": "human-in-loop-required",
            "wc_trend": "insufficient-data",
        }

    latest = eff_rows[0]

    # WC trend
    wc_values = [
        (r["wc_per_revenue"], r["end_date"])
        for r in eff_rows
        if r["wc_per_revenue"] is not None
    ]
    if len(wc_values) >= 2:
        newest = wc_values[0][0]
        oldest = wc_values[-1][0]
        if oldest == 0:
            wc_trend = "stable"
        elif newest < oldest * 0.95:
            wc_trend = "improving"  # less WC needed per revenue is better
        elif newest > oldest * 1.05:
            wc_trend = "deteriorating"
        else:
            wc_trend = "stable"
    else:
        wc_trend = "insufficient-data"

    # Per-capita status: ready only if every year in the window has a real
    # employee_count; partial if some years covered; otherwise human-in-loop.
    years_with_emp = sum(1 for r in eff_rows if r.get("employee_count") is not None)
    if years_with_emp == len(eff_rows):
        per_capita_status = "ready"
    elif years_with_emp > 0:
        per_capita_status = "partial"
    else:
        per_capita_status = "human-in-loop-required"

    return {
        "years_returned": len(eff_rows),
        "latest_end_date": (
            latest["end_date"].isoformat()
            if isinstance(latest["end_date"], date) else str(latest["end_date"])
        ),
        "wc_per_revenue_latest": latest.get("wc_per_revenue"),
        "fix_assets_per_revenue_latest": latest.get("fix_assets_per_revenue"),
        "revenue_per_labor_cost_latest": latest.get("revenue_per_labor_cost"),
        "revenue_per_employee_latest": latest.get("revenue_per_employee"),
        "profit_per_employee_latest": latest.get("profit_per_employee"),
        "per_capita_status": per_capita_status,
        "per_capita_years_covered": years_with_emp,
        "wc_trend": wc_trend,
    }


def _build_comparison(
    target_eff: list[dict[str, Any]],
    bench_eff: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build year-by-year comparison between target and benchmark."""
    bench_by_date = {}
    for r in bench_eff:
        key = r["end_date"].isoformat() if isinstance(r["end_date"], date) else str(r["end_date"])
        bench_by_date[key] = r

    comparison = []
    for t in target_eff:
        key = t["end_date"].isoformat() if isinstance(t["end_date"], date) else str(t["end_date"])
        b = bench_by_date.get(key, {})
        entry = {"end_date": key}
        for metric in ("wc_per_revenue", "fix_assets_per_revenue", "revenue_per_labor_cost", "profit_per_labor_cost"):
            tv = t.get(metric)
            bv = b.get(metric)
            entry[f"target_{metric}"] = tv
            entry[f"bench_{metric}"] = bv
            if tv is not None and bv is not None and bv != 0:
                entry[f"diff_{metric}"] = tv - bv
            else:
                entry[f"diff_{metric}"] = None
        comparison.append(entry)
    return comparison


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _fmt(value: Any) -> str:
    if _is_missing(value):
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            k: (
                None if _is_missing(v)
                else v.isoformat() if isinstance(v, date)
                else round(v, 6) if isinstance(v, float)
                else v
            )
            for k, v in row.items()
        }
        for row in rows
    ]


def _render_markdown(
    stock: str,
    as_of_date: date,
    lookback_years: int,
    profile: CompanyProfile,
    industry_info: dict[str, Any],
    eff_rows: list[dict[str, Any]],
    turnover_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    benchmark: dict[str, Any] | None,
    bench_eff: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    human_in_loop_requests: list[str] | None = None,
) -> str:
    lines = [
        "# look-06 Input-Output Efficiency",
        "",
        f"- stock: {stock}",
        f"- as_of_date: {as_of_date.isoformat()}",
        f"- lookback_years: {lookback_years}",
        f"- company_type: {profile.comp_type_label} ({profile.comp_type or 'unknown'})",
    ]
    if industry_info:
        lines.append(f"- industry: {industry_info.get('l1_name', '')} > {industry_info.get('l2_name', '')} > {industry_info.get('l3_name', '')} ({industry_info.get('peer_group_size', '?')} peers)")

    # Summary
    lines.extend(["", "## Summary", ""])
    lines.append(f"- years_returned: {summary['years_returned']}")
    lines.append(f"- wc_per_revenue_latest: {_fmt(summary.get('wc_per_revenue_latest'))}")
    lines.append(f"- fix_assets_per_revenue_latest: {_fmt(summary.get('fix_assets_per_revenue_latest'))}")
    lines.append(f"- revenue_per_labor_cost_latest: {_fmt(summary.get('revenue_per_labor_cost_latest'))}")
    lines.append(f"- per_capita_status: {summary.get('per_capita_status')}")
    lines.append(f"- revenue_per_employee_latest: {_fmt(summary.get('revenue_per_employee_latest'))}")
    lines.append(f"- profit_per_employee_latest: {_fmt(summary.get('profit_per_employee_latest'))}")
    lines.append(f"- wc_trend: {summary['wc_trend']}")

    # Per-capita 状态提示
    if summary.get("per_capita_status") in ("human-in-loop-required", "partial"):
        lines.append("")
        lines.append(
            "> ⚠️ 真实「人均营收 / 人均利润」需要年报员工总数。当前"
            + (
                "全部"
                if summary.get("per_capita_status") == "human-in-loop-required"
                else "部分"
            )
            + "年份未提供 employee_count，已跳过真实人均口径；"
            "`revenue_per_labor_cost` 仅代表「单位人力成本产出」，不能替代人均指标。"
        )

    # Efficiency table
    lines.extend(["", "## Efficiency Metrics", ""])
    eff_cols = [
        "end_date", "revenue", "working_capital", "wc_per_revenue",
        "fix_assets", "fix_assets_per_revenue",
        "c_paid_to_for_empl", "revenue_per_labor_cost", "profit_per_labor_cost",
        "employee_count", "revenue_per_employee", "profit_per_employee",
    ]
    lines.append("| " + " | ".join(eff_cols) + " |")
    lines.append("|" + "|".join("---" for _ in eff_cols) + "|")
    for row in eff_rows:
        lines.append("| " + " | ".join(_fmt(row.get(c)) for c in eff_cols) + " |")

    # Turnover table
    if turnover_rows:
        lines.extend(["", "## Turnover Indicators", ""])
        turn_cols = ["end_date", "ar_turn", "fa_turn", "assets_turn", "ca_turn"]
        lines.append("| " + " | ".join(turn_cols) + " |")
        lines.append("|" + "|".join("---" for _ in turn_cols) + "|")
        for row in turnover_rows:
            lines.append("| " + " | ".join(_fmt(row.get(c)) for c in turn_cols) + " |")

    # Benchmark comparison
    lines.extend(["", "## Benchmark Comparison", ""])
    if benchmark:
        lines.append(f"- benchmark: {benchmark['name']} ({benchmark['ts_code']})")
        lines.append(f"- benchmark_total_mv: {_fmt(benchmark['total_mv'])} (万元)")
        lines.append(f"- mv_trade_date: {benchmark.get('mv_trade_date', '')}")

        if comparison:
            lines.append("")
            comp_cols = [
                "end_date",
                "target_wc_per_revenue", "bench_wc_per_revenue", "diff_wc_per_revenue",
                "target_fix_assets_per_revenue", "bench_fix_assets_per_revenue",
                "target_revenue_per_labor_cost", "bench_revenue_per_labor_cost",
            ]
            lines.append("| " + " | ".join(comp_cols) + " |")
            lines.append("|" + "|".join("---" for _ in comp_cols) + "|")
            for row in comparison:
                lines.append("| " + " | ".join(_fmt(row.get(c)) for c in comp_cols) + " |")
    else:
        lines.append("- benchmark: not available (no SW L3 peers or market cap data)")

    if human_in_loop_requests:
        lines.extend(["", "## Human-in-Loop Requests", ""])
        for i, req in enumerate(human_in_loop_requests, 1):
            lines.append(f"{i}. {req}")

    return "\n".join(lines)


def _render_json(
    stock: str,
    as_of_date: date,
    lookback_years: int,
    profile: CompanyProfile,
    industry_info: dict[str, Any],
    eff_rows: list[dict[str, Any]],
    turnover_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    benchmark: dict[str, Any] | None,
    bench_eff: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    human_in_loop_requests: list[str],
) -> str:
    per_capita_status = summary.get("per_capita_status", "human-in-loop-required")
    if summary["years_returned"] == 0:
        status = "no-data"
    elif per_capita_status == "human-in-loop-required":
        # 数据库拿到了结构化 WC / 固定资产指标，但人均口径需要用户补数据。
        status = "partial"
    else:
        status = "ready"

    payload = {
        "rule_id": "look-06",
        "status": status,
        "stock": stock,
        "as_of_date": as_of_date.isoformat(),
        "lookback_years": lookback_years,
        "company_profile": profile.to_payload(),
        "industry_info": industry_info,
        "summary": summary,
        "efficiency_rows": _serialize_rows(eff_rows),
        "turnover_indicators": _serialize_rows(turnover_rows),
        "benchmark": benchmark,
        "benchmark_efficiency_rows": _serialize_rows(bench_eff),
        "comparison": _serialize_rows(comparison),
        "human_in_loop_requests": human_in_loop_requests,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run look-06 input-output efficiency analysis"
    )
    parser.add_argument("--stock", required=True)
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--lookback-years", type=int, default=3)
    parser.add_argument("--db-path", default=str(default_db_path()))
    parser.add_argument(
        "--employee-count-bundle",
        default=None,
        help=(
            "JSON 文件，人工提供真实员工人数，用于计算人均营收/利润。"
            " 格式: [{\"ts_code\":\"600660.SH\",\"year\":2025,\"employee_count\":33000}]。"
            " 禁止填写代理值（如工资/平均薪酬）。未提供时脚本返回 human-in-loop-required。"
        ),
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()

    if args.lookback_years <= 0:
        raise SystemExit("--lookback-years must be a positive integer")

    as_of_date = parse_date(args.as_of_date)
    db_path = Path(args.db_path).expanduser().resolve()

    employee_bundle_path = (
        Path(args.employee_count_bundle).expanduser().resolve()
        if args.employee_count_bundle
        else None
    )
    if employee_bundle_path is not None and not employee_bundle_path.exists():
        raise SystemExit(f"--employee-count-bundle file not found: {employee_bundle_path}")
    employee_bundle = _load_employee_bundle(employee_bundle_path)

    with connect_read_only(db_path) as con:
        profile = detect_company_profile(con, args.stock, as_of_date)

        if profile.is_financial:
            payload = {
                "rule_id": "look-06",
                "status": "not-applicable",
                "stock": args.stock,
                "as_of_date": as_of_date.isoformat(),
                "lookback_years": args.lookback_years,
                "company_profile": profile.to_payload(),
                "warning": profile.warning,
                "reason": "当前规则针对一般工商业公司设计，金融类公司的投入产出指标口径不可直接类比。",
            }
            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print("\n".join([
                    "# look-06 Input-Output Efficiency",
                    "",
                    "## Not Applicable",
                    f"- stock: {args.stock}",
                    f"- warning: {profile.warning or ''}",
                    f"- reason: {payload['reason']}",
                ]))
            return

        # Target stock data
        raw_rows = _fetch_efficiency_inputs(con, args.stock, as_of_date, args.lookback_years)
        turnover_rows = _fetch_turnover_indicators(con, args.stock, as_of_date, args.lookback_years)
        industry_info = _fetch_peer_industry_info(con, args.stock)

        # Benchmark
        benchmark = _find_benchmark(con, args.stock, as_of_date)
        bench_raw = []
        if benchmark:
            bench_raw = _fetch_efficiency_inputs(con, benchmark["ts_code"], as_of_date, args.lookback_years)

    # Compute
    eff_rows = _compute_efficiency(raw_rows, employee_bundle, args.stock)
    bench_eff = _compute_efficiency(bench_raw, employee_bundle, benchmark["ts_code"] if benchmark else None)
    summary = _build_summary(eff_rows)
    comparison = _build_comparison(eff_rows, bench_eff) if benchmark else []

    # Human-in-loop requests (人均口径数据缺口)
    human_in_loop_requests: list[str] = []
    per_capita_status = summary.get("per_capita_status")
    if per_capita_status in ("human-in-loop-required", "partial"):
        missing_years = [
            (r["end_date"].year if isinstance(r["end_date"], date) else str(r["end_date"])[:4])
            for r in eff_rows
            if r.get("employee_count") is None
        ]
        years_str = ", ".join(str(y) for y in missing_years)
        human_in_loop_requests.append(
            "请提供以下年度的真实员工总数（来源：年报「员工情况」章节的在岗员工数合计），"
            f"目标股票 {args.stock}，缺口年份：[{years_str}]。"
            " 通过 --employee-count-bundle 传入 JSON："
            " [{\"ts_code\":\"" + args.stock + "\",\"year\":YYYY,\"employee_count\":N}]。"
            " 禁止使用 `c_paid_to_for_empl / 假设年薪` 等代理估算。"
        )

    if args.format == "json":
        print(_render_json(
            args.stock, as_of_date, args.lookback_years, profile,
            industry_info, eff_rows, turnover_rows, summary,
            benchmark, bench_eff, comparison, human_in_loop_requests,
        ))
    else:
        print(_render_markdown(
            args.stock, as_of_date, args.lookback_years, profile,
            industry_info, eff_rows, turnover_rows, summary,
            benchmark, bench_eff, comparison, human_in_loop_requests,
        ))


if __name__ == "__main__":
    main()
