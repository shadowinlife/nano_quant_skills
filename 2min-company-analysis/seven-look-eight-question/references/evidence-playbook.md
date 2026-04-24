# 八问 Evidence Playbook

本文档给出八问每题的**证据优先级**与**来源 URL 模板**，供 Agent 在执行 `eight_questions_orchestrator.py` 时自检。

## 通用铁律

1. 每题至少 1 条 `primary`/`regulatory`/`db` 证据才允许 `rating`。
2. `industry_report` 与 `ir_meeting` 必须在 Markdown 报告中显式打标签。
3. 若 `nano_search_mcp` 某工具抛异常或返回 `source=unavailable`：
   - 对应证据槽位 → 留空
   - `missing_inputs` 追加人工取证任务
   - 禁止用模型常识替代

## Q1 行业前景
- 事实: `idx_sw_l3_peers`（申万 L1/L2/L3）
- 政策: `fetch_industry_policy_list(industry_sw_l2=...)` — gov.cn
- 观点: `fetch_industry_report_list(ts_code=...)` — 券商研报
- 追问: 若 L2 映射缺失，需人工提供行业分类后再复跑

## Q2 竞争优势
- 事实: `fin_mainbz`（近 3 年主营毛利结构）, `idx_sw_l3_peers`
- 事实文本: `fetch_reports(stockid, 'annual', fetch_content=True)` → MD&A 段落
- 追问: 年报正文抓取失败需人工上传年报 URL 或 PDF

## Q3 管理团队
- DB 事实: `stk_company`, `stk_managers`, `stk_rewards`, `fin_top10_holders`
- 变动证据: `fetch_announcement_list` + 关键词 `辞职/聘任/换届/高管/董事/监事`
- 追问: 近 12 个月高管变动 >3 次需人工核查是否存在治理动荡

## Q4 财务真实性
- DB 事实: `fin_indicator.ocf_to_profit`（净现比）, `stk_name_history`
- 事实证据: `fetch_announcement_list` + 关键词 `审计/非标/保留意见/问询/关注函/立案/更正/更名`
- Rating 规则: red_flags ≥3 → 2；≥1 → 3；0 → 4；(无 DB 证据 → insufficient)

## Q5 市场地位
- DB 事实: `fin_mainbz`, `idx_sw_l3_peers`
- 事实文本: 年报正文 "前五大客户 / 前五大供应商" 段落
- 追问: 同行市占率需用 `peer_ts_code` 批量查 `fin_income.total_revenue` 自行计算

## Q6 业务模式
- DB 事实: `fin_mainbz`（≥5 年以观察结构变化）
- 事实文本: 年报 "公司业务概要 / 主要经营模式"
- 判断: 条目年际变化 ≤20% 且主营收入占比 >60% → 稳定

## Q7 风险因素
- DB 事实: `stk_pledge_stat`（质押比例阈值 10%/30%）, `stk_st_daily`
- 事实证据: `fetch_penalty_list(ts_code)`, `fetch_announcement_list` + 风险关键词
- Rating: red_flags 0→4, 1-2→3, 3-4→2, ≥5→1

## Q8 未来规划
- DB 事实: `fin_forecast`, `fin_express`
- 公司口径: `fetch_ir_meeting_list` —— 渲染时加 `[公司口径·IR 调研]`
- 事实文本: 年报 "未来展望 / 经营计划"
