#!/usr/bin/env python3
"""按 index_code 循环的 Tushare 同步脚本 — index_weight（指数成分和权重）。

适用接口（必须传 index_code 的）:
  - index_weight    - 指数成分和权重

职责：
  - 从 idx_info 读全市场 index_code
  - 对每个 index_code 按日期范围调 Tushare API，累积 DataFrame，按批次 flush 到 DuckDB
  - 在 table_sync_state 中以 dimension_type='index_code' + dimension_value=index_code 记录进度
  - 支持断点续传
  - 空 payload 记成功（某些指数可能没有成分数据）
  - 失败的 index_code 记失败，下次重跑

用法::

    TUSHARE_TOKEN=xxx python etl/sync_by_index_code.py \\
        --endpoint index_weight \\
        --target-table idx_weight \\
        --duckdb-path data/ashare.duckdb \\
        --start-date 20240101 \\
        --end-date 20240131 \\
        [--batch-size 50] [--sleep 0.1]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger


def _get_tushare():
    import tushare as ts
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        sys.exit("TUSHARE_TOKEN not set")
    return ts.pro_api(token=token)


def _ensure_sync_state(con: duckdb.DuckDBPyConnection) -> None:
    """Ensure table_sync_state exists"""
    con.execute("""
        CREATE TABLE IF NOT EXISTS table_sync_state (
            source_table VARCHAR,
            dimension_type VARCHAR,
            dimension_value VARCHAR,
            is_sync INTEGER,
            error_message VARCHAR,
            updated_at TIMESTAMP
        )
    """)


def _load_index_codes(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Load all index codes from idx_info"""
    try:
        rows = con.execute(
            "SELECT DISTINCT ts_code FROM idx_info WHERE ts_code IS NOT NULL ORDER BY ts_code"
        ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        logger.warning("idx_info table not found, will skip index_code filtering")
        return []


def _load_synced(con: duckdb.DuckDBPyConnection, source_table: str) -> set[str]:
    """Load already synced index_codes"""
    rows = con.execute(
        """SELECT dimension_value FROM table_sync_state
           WHERE source_table = ? AND dimension_type = 'index_code' AND is_sync = 1""",
        [source_table],
    ).fetchall()
    return {r[0] for r in rows}


def _write_state(
    con: duckdb.DuckDBPyConnection,
    source_table: str,
    index_code: str,
    success: bool,
    err: str = "",
) -> None:
    """Write sync status for index_code"""
    con.execute(
        """DELETE FROM table_sync_state
           WHERE source_table = ? AND dimension_type = 'index_code'
             AND dimension_value = ?""",
        [source_table, index_code],
    )
    con.execute(
        """INSERT INTO table_sync_state
           (source_table, dimension_type, dimension_value, is_sync, error_message, updated_at)
           VALUES (?, 'index_code', ?, ?, ?, ?)""",
        [source_table, index_code, 1 if success else 0, err, datetime.now()],
    )


def _flush(
    con: duckdb.DuckDBPyConnection,
    batch_df: pd.DataFrame,
    target_table: str,
    mode: str,
) -> int:
    """Flush batch to DuckDB"""
    if batch_df.empty:
        return 0
    
    # Ensure target table exists (auto-create from first batch schema)
    existing = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [target_table.strip('"')]
    ).fetchone()[0]
    if not existing:
        con.execute(
            f"CREATE TABLE IF NOT EXISTS {target_table} AS SELECT * FROM batch_df LIMIT 0"
        )

    if mode == "overwrite":
        con.execute(f"DELETE FROM {target_table}")

    con.execute(f"INSERT INTO {target_table} SELECT * FROM batch_df")
    return len(batch_df)


def main():
    parser = argparse.ArgumentParser(description="Sync index_weight by index_code")
    parser.add_argument("--endpoint", required=True, help="Tushare endpoint (index_weight)")
    parser.add_argument("--target-table", required=True, help="Target DuckDB table")
    parser.add_argument("--duckdb-path", required=True, help="DuckDB file path")
    parser.add_argument("--start-date", required=True, help="Start date YYYYMMDD")
    parser.add_argument("--end-date", required=True, help="End date YYYYMMDD")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size")
    parser.add_argument("--sleep", type=float, default=0.1, help="Sleep between API calls")
    parser.add_argument("--mode", default="append", choices=["append", "overwrite"], 
                       help="Insert mode")
    parser.add_argument("--sync-all", action="store_true", help="Re-sync all index_codes")
    
    args = parser.parse_args()
    
    logger.info(f"Starting sync_by_index_code: {args.endpoint}")
    logger.info(f"  Target: {args.target_table}")
    logger.info(f"  Period: {args.start_date} to {args.end_date}")
    logger.info(f"  DuckDB: {args.duckdb_path}")
    
    # Setup
    pro = _get_tushare()
    con = duckdb.connect(args.duckdb_path)
    _ensure_sync_state(con)
    
    # Get index codes
    index_codes = _load_index_codes(con)
    if not index_codes:
        logger.error("No index codes found in idx_info. Please sync idx_info first.")
        return 1
    
    logger.info(f"Found {len(index_codes)} index codes")
    
    # Filter synced
    if not args.sync_all:
        synced = _load_synced(con, args.endpoint)
        index_codes = [ic for ic in index_codes if ic not in synced]
        logger.info(f"After filtering: {len(index_codes)} codes to sync")
    
    if not index_codes:
        logger.info("All index codes already synced")
        return 0
    
    # Sync loop
    batch_df = pd.DataFrame()
    batch_count = 0
    failed_codes = []
    
    for idx, index_code in enumerate(index_codes, 1):
        try:
            logger.info(f"[{idx}/{len(index_codes)}] Fetching {index_code}")
            
            # Call Tushare API
            df = pro.index_weight(
                index_code=index_code,
                start_date=args.start_date,
                end_date=args.end_date,
            )
            
            if df is None or df.empty:
                logger.info(f"  No data for {index_code}")
                _write_state(con, args.endpoint, index_code, True)
                time.sleep(args.sleep)
                continue
            
            logger.info(f"  Got {len(df)} rows")
            batch_df = pd.concat([batch_df, df], ignore_index=True)
            batch_count += len(df)
            
            # Flush batch
            if batch_count >= args.batch_size:
                rows_written = _flush(con, batch_df, args.target_table, args.mode)
                logger.info(f"  Flushed batch: {rows_written} rows written")
                batch_df = pd.DataFrame()
                batch_count = 0
            
            _write_state(con, args.endpoint, index_code, True)
            time.sleep(args.sleep)
            
        except Exception as e:
            logger.error(f"  Error for {index_code}: {e}")
            _write_state(con, args.endpoint, index_code, False, str(e))
            failed_codes.append(index_code)
            time.sleep(args.sleep * 2)  # Back off on error
            continue
    
    # Final flush
    if not batch_df.empty:
        rows_written = _flush(con, batch_df, args.target_table, args.mode)
        logger.info(f"Final flush: {rows_written} rows written")
    
    # Summary
    logger.info(f"Sync complete")
    logger.info(f"  Total codes: {len(index_codes)}")
    logger.info(f"  Failed: {len(failed_codes)}")
    
    if failed_codes:
        logger.info(f"  Failed codes: {', '.join(failed_codes)}")
    
    con.close()
    return 1 if failed_codes else 0


if __name__ == "__main__":
    sys.exit(main())
