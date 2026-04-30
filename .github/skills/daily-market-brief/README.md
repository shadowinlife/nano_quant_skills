# daily-market-brief

daily-market-brief 是一个自包含的 Python skill，用来按交易日生成 A 股盘前核心新闻聚合简报。

## 模块目标

- 在一个入口里协调五个模块：美股热点、主流财经媒体、自媒体共识、研报动态、大宗商品。
- 先产出可发布的 temp 版，再在剩余模块完成后补 final 版。
- 同时落盘结构化 JSON 中间结果和 Markdown 报告，便于审阅和二次处理。

## 目录地图

- `config/`：示例配置、跟踪清单、执行阶段说明。
- `docs/`：来源评估、自动化边界、快速开始和维护文档。
- `src/`：CLI、聚合器、模块实现、数据源适配器、工具函数。
- `tests/`：contract、integration、unit 和 mock fixtures。
- `tmp/`：运行时输出、缓存和临时工作报告。

## 环境准备

```bash
conda activate legonanobot
pip install -r .github/skills/daily-market-brief/requirements.txt
cp .github/skills/daily-market-brief/config/config.example.yaml \
  .github/skills/daily-market-brief/config/local.yaml
```

如果启用 tushare 生产源，需要在当前 shell 临时导出 `TUSHARE_TOKEN`。

## 执行入口

查看 CLI 帮助：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py --help
```

按交易日自动执行 temp/final：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --stage auto
```

只跑部分模块：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --modules us_market,media_mainline,commodities
```

跳过预检（CI/离线场景）：

```bash
conda run -n legonanobot python .github/skills/daily-market-brief/src/main.py \
  --date 2026-04-29 \
  --config .github/skills/daily-market-brief/config/local.yaml \
  --skip-preflight
```

## 退出码

| 代码 | 含义 |
|------|-----|
| `0` | 正常完成 |
| `3` | 部分模块缺数据（strict 模式或关键模块失败） |
| `4` | 预检失败 — stderr 输出 `PREFLIGHT_FAIL: <缺少的依赖>` |
| `5` | 内部未预期异常 — stderr 输出 `INTERNAL_ERROR: <消息>` |

## 产物布局

- 模块 JSON：`tmp/<trade-date>/module-results/*.json`
- 聚合 JSON：`tmp/<trade-date>/report/report.<stage>.json`
- Markdown 报告：`tmp/<trade-date>/report/report.<stage>.md`
- 运行摘要：`tmp/<trade-date>/report/run-summary.json`（FR-027）
- 临时工作报告：`tmp/work-reports/*.md`

## 验证入口

```bash
pytest .github/skills/daily-market-brief/tests/ -v
conda run -n legonanobot python .github/skills/daily-market-brief/src/validate_daily_run.py
./.github/skills/daily-market-brief/validate-daily-run.sh
```

Windows 环境使用 Python 验证脚本，不依赖 shell wrapper。

## 自动化边界

- temp 版默认只要求关键模块 `us_market` 和 `media_mainline` 成功。
- `social_consensus` 与 `research_reports` 支持自动提取，但结果可以带 review 标记。
- 凭据、绝对路径和本机缓存不允许进入仓库。

## Operator Handoff

自动流程跑完后，操作者主要看三件事：

1. temp 报告里的关键主线是否能直接支持盘前判断。
2. final 报告里哪些 `source_missing` 或 `review_required` 需要补修订。
3. 哪些 tracking item 应该在下一轮升降级或停用。

## 配置维护例子

- 想扩大社媒覆盖：先在 `tracking-lists.yaml` 里新增 `priority: extended` 的账号。
- 想缩小范围：优先把对象改成 `enabled: false`（同时必须设置 `disabled_reason`），而不是直接删除。
- 改完配置后建议先跑：`pytest .github/skills/daily-market-brief/tests/integration/test_config_update_roundtrip.py -q`

## 可观测性摘要 (FR-027)

每次运行在 `tmp/<date>/report/run-summary.json` 产出一份结构化摘要，包含：

- `preflight.ok` / `preflight.missing`：预检状态
- `modules[].final_status`：各模块最终状态
- `modules[].attempted_sources`：已尝试的数据源及失败分类 (`fail_class`)
- `modules[].semantic_drift`：语义标签漂移检测结果
- `coverage_summary`：各覆盖状态的计数汇总

Markdown 报告若检测到以下情况会在模块头部附加提示行：

- `⚠️ 语义漂移检测：<漂移维度>` — 数据源语义标签与声明不符
- `⚠️ 行情滞后：N 条行情数据与目标日期差距超过 5 个自然日`