# Index Weight 指数成分和权重数据同步指南

## 概述

本指南说明如何将 Tushare 的指数成分和权重数据（`index_weight` API）集成到 DuckDB 同步框架中。

**API 文档**：https://tushare.pro/document/2?doc_id=96

| 属性 | 值 |
|------|-----|
| Tushare 接口 | `index_weight` |
| DuckDB 目标表 | `idx_weight` |
| 维度类型 | `trade_date`（按交易日增量） |
| 循环维度 | `index_code`（需要从 idx_info 获取） |
| 数据粒度 | 指数 × 成分股 × 交易日 |
| 主键 | `index_code, con_code, trade_date` |

## 数据结构

### 输入参数
```python
# 必需参数
index_code: str  # 指数代码（如 '000300.SH' for 沪深300）

# 可选参数
trade_date: str      # 单个交易日 YYYYMMDD
start_date: str      # 开始日期 YYYYMMDD
end_date: str        # 结束日期 YYYYMMDD
```

### 输出字段
```python
index_code: str      # 指数代码
con_code: str        # 成分代码（股票代码）
trade_date: str      # 交易日期
weight: float        # 权重（%）
```

### 表结构（自动创建）
```sql
CREATE TABLE idx_weight (
    index_code VARCHAR,
    con_code VARCHAR,
    trade_date VARCHAR,
    weight DOUBLE,
    PRIMARY KEY (index_code, con_code, trade_date)
);
```

## 快速开始

### 1. 确保 idx_info 表已同步

`index_weight` 同步依赖 `idx_info` 表来获取所有可用的指数代码。首先确保已同步指数基础信息：

```bash
TUSHARE_TOKEN=your_token python tushare_duckdb_sync_scripts/run_snapshot_refresh.py \
  --tables idx_info
```

验证表存在：
```bash
python -c "import duckdb; con = duckdb.connect('data/ashare.duckdb'); \
  print(con.execute('SELECT COUNT(*) FROM idx_info').fetchone())"
```

### 2. 同步指数成分和权重

**最简单的方式**：

```bash
TUSHARE_TOKEN=your_token python tushare_duckdb_sync_scripts/run_index_weight_sync.py \
  --start-date 20240101 \
  --end-date 20240131
```

**参数说明**：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--start-date` | 同步开始日期 YYYYMMDD | 当前日期往前 30 天 |
| `--end-date` | 同步结束日期 YYYYMMDD | 今天 |
| `--lookback-days` | 默认回看天数 | 30 |
| `--batch-size` | 每批处理的行数 | 50 |
| `--sleep` | API 调用间隔（秒） | 0.1 |
| `--sync-all` | 重新同步所有指数（忽略已同步） | False |
| `--duckdb-path` | DuckDB 文件路径 | `data/ashare.duckdb` |
| `--dry-run` | 只显示执行计划，不实际同步 | False |

**示例**：

```bash
# 同步最近 30 天（默认）
TUSHARE_TOKEN=xxx python tushare_duckdb_sync_scripts/run_index_weight_sync.py

# 同步特定时间段
TUSHARE_TOKEN=xxx python tushare_duckdb_sync_scripts/run_index_weight_sync.py \
  --start-date 20240101 \
  --end-date 20240131

# 重新同步所有指数（清空现有数据）
TUSHARE_TOKEN=xxx python tushare_duckdb_sync_scripts/run_index_weight_sync.py \
  --sync-all \
  --start-date 20240101 \
  --end-date 20240131

# 预览执行计划
python tushare_duckdb_sync_scripts/run_index_weight_sync.py \
  --start-date 20240101 \
  --end-date 20240131 \
  --dry-run
```

## 集成到现有同步流程

### 方式 1: 从 run_all.py 调用

编辑 `run_all.py`，在现有任务之后添加：

```python
# 在 run_trade_date_incremental 之后添加
def main():
    # ... existing code ...
    
    # Run index_weight sync
    index_weight_result = subprocess.run([
        sys.executable,
        str(WORKSPACE_ROOT / "tushare_duckdb_sync_scripts" / "run_index_weight_sync.py"),
        "--start-date", start_date,
        "--end-date", end_date,
    ], env={**os.environ, "TUSHARE_TOKEN": token})
    
    if index_weight_result.returncode != 0:
        logger.error("index_weight sync failed")
        return 1
```

### 方式 2: 从 crontab 调用

添加到 crontab：

```bash
# 每天 20:00 运行指数成分权重同步（前一交易日）
0 20 * * 1-5 TUSHARE_TOKEN=xxx /bin/bash -c 'cd /path/to/workspace && conda run -n legonanobot python tushare_duckdb_sync_scripts/run_index_weight_sync.py --lookback-days 1'
```

## 下游使用示例

### 查询最新权重

```sql
-- 查询沪深300的最新成分权重
SELECT 
  con_code,
  weight,
  trade_date
FROM idx_weight
WHERE index_code = '000300.SH'
  AND trade_date = (
    SELECT MAX(trade_date) 
    FROM idx_weight 
    WHERE index_code = '000300.SH'
  )
ORDER BY weight DESC
LIMIT 10;
```

### 计算权重变化

```sql
-- 计算沪深300本月权重变化
WITH monthly_data AS (
  SELECT 
    con_code,
    weight,
    trade_date,
    ROW_NUMBER() OVER (PARTITION BY con_code ORDER BY trade_date DESC) as rn
  FROM idx_weight
  WHERE index_code = '000300.SH'
    AND trade_date BETWEEN '20240101' AND '20240131'
)
SELECT 
  con_code,
  MAX(CASE WHEN rn = 1 THEN weight END) as latest_weight,
  MAX(CASE WHEN rn = (SELECT COUNT(*) FROM monthly_data m2 WHERE m2.con_code = monthly_data.con_code) 
       THEN weight END) as earliest_weight,
  MAX(CASE WHEN rn = 1 THEN weight END) - 
    MAX(CASE WHEN rn = (SELECT COUNT(*) FROM monthly_data m2 WHERE m2.con_code = monthly_data.con_code) 
         THEN weight END) as weight_change
FROM monthly_data
GROUP BY con_code
ORDER BY weight_change DESC;
```

## 故障排查

### 问题 1: "idx_info table not found"

**原因**：`idx_info` 表未同步  
**解决**：先运行 `run_snapshot_refresh.py --tables idx_info`

### 问题 2: "No data for index_code"

**原因**：某个指数在该时间段没有成分数据（正常情况）  
**解决**：脚本会自动跳过，这是正常行为

### 问题 3: API 限流错误

**原因**：调用 API 过于频繁  
**解决**：增加 `--sleep` 参数值，或者减少 `--batch-size`

```bash
python tushare_duckdb_sync_scripts/run_index_weight_sync.py \
  --sleep 0.5 \
  --batch-size 20
```

### 问题 4: "TUSHARE_TOKEN not set"

**原因**：未设置 token 环境变量  
**解决**：
```bash
export TUSHARE_TOKEN=your_token_here
python tushare_duckdb_sync_scripts/run_index_weight_sync.py
```

## 性能优化建议

1. **按月同步而非全量**：每次只同步 1 个月数据，避免超时
2. **使用合理的 batch_size**：默认 50 比较稳定，不要过小（会增加 API 调用次数）
3. **分散同步时间**：不要在市场交易时间段大量同步
4. **监控表大小**：
   ```sql
   SELECT COUNT(*) FROM idx_weight;
   ```

## 监控和日志

日志输出到：`tushare_duckdb_sync_scripts/logs/tushare_sync/`

查看最新日志：
```bash
tail -f tushare_duckdb_sync_scripts/logs/tushare_sync/*.log
```

关键日志事件：
- `sync_task_started` - 同步任务开始
- `sync_task_completed` - 同步任务完成
- `index_weight_sync` - 错误消息

## 参考资源

- Tushare 官方文档：https://tushare.pro/document/2?doc_id=96
- DuckDB 文档：https://duckdb.org/docs/
- 本项目 README：../README.md
