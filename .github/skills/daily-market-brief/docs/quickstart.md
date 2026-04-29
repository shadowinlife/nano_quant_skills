# Implementation Quickstart

## 目标

用最短路径把 daily-market-brief 跑起来，并确认 temp/final 报告、配置加载和验证脚本都正常。

## 环境准备

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

如果启用了 tushare 生产源，只在当前 shell 会话里临时设置 `TUSHARE_TOKEN`。

## 最小运行步骤

1. 检查配置：确认 `critical_modules` 包含 `us_market` 和 `media_mainline`。
2. 检查 tracking lists：至少保留 social、research、commodities 三类 core 对象。
3. 先跑 help 和 validate，再跑主流程。

## 验证命令

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py --help
conda run -n legonanobot python .github/skills/daily-market-brief/src/validate_daily_run.py
pytest .github/skills/daily-market-brief/tests/ -q
```

macOS/Linux 还可以跑 POSIX wrapper：

```bash
./.github/skills/daily-market-brief/validate-daily-run.sh
```

Windows 不使用 shell wrapper，直接跑 Python fallback：

```powershell
conda run -n legonanobot python .github/skills/daily-market-brief/src/validate_daily_run.py
```

## 执行主流程

自动 temp/final：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --stage auto
```

只出 temp：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --stage temp
```

只跑部分模块：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --modules us_market,media_mainline,commodities
```

## 产物位置

- 模块 JSON：`.github/skills/daily-market-brief/tmp/<trade-date>/module-results/*.json`
- 聚合 JSON：`.github/skills/daily-market-brief/tmp/<trade-date>/report/report.<stage>.json`
- Markdown 报告：`.github/skills/daily-market-brief/tmp/<trade-date>/report/report.<stage>.md`
- 临时工作报告：`.github/skills/daily-market-brief/tmp/work-reports/*.md`

## 平台说明

- macOS/Linux：支持直接运行 shell wrapper
- Windows：使用 Python validation fallback，不依赖 bash
- 三个平台都走同一个 `validate_daily_run.py` 核心逻辑，保证检查口径一致