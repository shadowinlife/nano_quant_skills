"""external_evidence_collectors.py — 对 nano_search_mcp 工具的统一封装。

设计目标
--------
1. 把 MCP tool 当普通 Python 模块 import，零进程开销。
2. 任何 MCP 异常 → 返回 `CollectResult(evidence=[], status="insufficient-evidence",
   error=msg, error_type=...)`，绝不让上游抛异常；也绝不伪造证据。
3. 统一的返回形状：`CollectResult(evidence, status, missing_inputs, error, error_type)`。
4. 每条证据均会经 `Evidence.__post_init__` 强校验，保证 excerpt 非空。
5. ``error_type`` 语义化：
   - ``env_missing``  — 环境变量缺失（如 DASHSCOPE_API_KEY）；**必须人工介入**，不做降级。
   - ``network_fail`` — MCP 调用失败/超时；可降级为 partial。
   - ``not_found``    — MCP 调通但无匹配结果；不算失败。
   - ``module_missing`` — nano_search_mcp 未安装；人工介入。
   - ``upstream_contract_break`` — MCP 返回结构异常（JSON 解析/字段缺失/类型错）；必须人工介入。
   - ``source_disabled`` — 数据源永久不可用（例如上游接口被下线）；必须人工介入。

重要：本模块只做"取证"，不做"评分"。评分交给 q0N 模块。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

try:
    from .eight_questions_domain import Evidence, SourceType, now_iso, stockid_from_ts_code
except ImportError:
    from eight_questions_domain import Evidence, SourceType, now_iso, stockid_from_ts_code


logger = logging.getLogger(__name__)


# 最长 excerpt（字符）——防止整篇年报塞进 JSON
_EXCERPT_MAX_CHARS = 600


# ---------------------------------------------------------------------------
# 统一返回结构
# ---------------------------------------------------------------------------


@dataclass
class CollectResult:
    evidence: list[Evidence] = field(default_factory=list)
    status: str = "insufficient-evidence"  # ready | partial | insufficient-evidence
    missing_inputs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    error: str | None = None
    # 新增：错误分类，供 qNN 决定降级策略
    # env_missing | network_fail | not_found | module_missing | upstream_contract_break | source_disabled
    error_type: str | None = None

    def extend(self, other: "CollectResult") -> None:
        self.evidence.extend(other.evidence)
        self.missing_inputs.extend(other.missing_inputs)
        self.notes.extend(other.notes)
        if other.error and not self.error:
            self.error = other.error
        if other.error_type and not self.error_type:
            self.error_type = other.error_type

    @property
    def requires_human(self) -> bool:
        """env_missing / module_missing / upstream_contract_break / source_disabled 必须人工介入。"""
        return self.error_type in (
            "env_missing",
            "module_missing",
            "upstream_contract_break",
            "source_disabled",
        )


def _truncate(text: str, limit: int = _EXCERPT_MAX_CHARS) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


# ---------------------------------------------------------------------------
# 环境校验：DASHSCOPE_API_KEY 硬拦截
# ---------------------------------------------------------------------------


_BAILIAN_DEP_TOOLS = ("industry_policies", "deferred_search", "search (WebSearch)")


def check_bailian_env() -> tuple[bool, str | None]:
    """返回 (ok, missing_reason)。仅在需要调用百炼/WebSearch 的工具前使用。

    这里不做 3 次重试才失败——缺 key 是确定性问题，立刻要求人工。
    """
    if not os.getenv("DASHSCOPE_API_KEY"):
        return False, (
            "CRITICAL: 未检测到环境变量 DASHSCOPE_API_KEY。"
            f"依赖百炼 WebSearch 的工具（{', '.join(_BAILIAN_DEP_TOOLS)}）将无法工作。"
            " 请在 shell 中 `export DASHSCOPE_API_KEY=sk-...` 后重新执行。"
        )
    return True, None


# 结构性错误异常类型：JSON 解析失败、字段缺失、类型不符等。
# 这些错误几乎都是上游 MCP 工具 contract 变化引起，需要人工修库。
_CONTRACT_BREAK_EXC_TYPES: tuple[type[BaseException], ...] = (
    json.JSONDecodeError,
    KeyError,
    AttributeError,
    TypeError,
)


def _classify_mcp_error(exc: BaseException) -> str:
    """按异常类型 + 消息分类。

    优先级：env_missing > upstream_contract_break > network_fail。
    """
    msg = str(exc)
    if "DASHSCOPE_API_KEY" in msg or "缺少环境变量" in msg:
        return "env_missing"
    # 结构性异常单独归类——不可通过重试恢复
    if isinstance(exc, _CONTRACT_BREAK_EXC_TYPES):
        return "upstream_contract_break"
    if any(kw in msg for kw in ("timeout", "Timeout", "Connection", "ConnectError", "服务不可用")):
        return "network_fail"
    return "network_fail"


# ---------------------------------------------------------------------------
# 年报/定期报告（新浪 sina_reports）
# ---------------------------------------------------------------------------


def collect_annual_reports(
    ts_code: str,
    *,
    limit: int = 3,
    fetch_content: bool = False,
) -> CollectResult:
    """抓取最近 N 份年报 listing。默认不下载正文（昂贵）。

    正文抓取交给下游按需调用 `fetch_announcement_text(source_url)`。
    """
    result = CollectResult()
    try:
        from nano_search_mcp.tools.sina_reports import fetch_reports
    except ImportError as exc:
        result.error = f"nano_search_mcp 不可用: {exc}"
        result.error_type = "module_missing"
        result.missing_inputs.append("🔴 [人工介入] 安装 nano_search_mcp 模块")
        return result

    stockid = stockid_from_ts_code(ts_code)
    try:
        data = fetch_reports(
            stockid, "annual", limit=limit, fetch_content=fetch_content
        )
    except Exception as exc:  # noqa: BLE001
        result.error = f"fetch_reports(annual) 失败: {exc}"
        result.error_type = _classify_mcp_error(exc)
        result.missing_inputs.append(f"手动提供 {ts_code} 最近 {limit} 年年报 URL（MCP 失败）")
        return result

    retrieved_at = now_iso()
    for rep in data.get("reports", []):
        url = rep.get("url") or rep.get("source_url") or ""
        title = rep.get("title", "")
        content = rep.get("content") or title
        if not url or not content:
            continue
        try:
            result.evidence.append(
                Evidence(
                    source_type=SourceType.PRIMARY,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    excerpt=_truncate(content),
                    title=title,
                )
            )
        except ValueError:
            continue

    result.status = "ready" if result.evidence else "insufficient-evidence"
    if not result.evidence:
        result.missing_inputs.append(f"{ts_code} 年报 listing 为空，请人工补证")
    return result


# ---------------------------------------------------------------------------
# 普通公告（审计/问询/立案/诉讼等）
# ---------------------------------------------------------------------------


def collect_announcements(
    ts_code: str,
    *,
    keywords: list[str] | None = None,
    start_date: str = "",
    end_date: str = "",
    limit: int = 20,
) -> CollectResult:
    """抓取公告列表并按关键词过滤标题。"""
    result = CollectResult()
    try:
        from nano_search_mcp.tools.announcements import fetch_announcement_list
    except ImportError as exc:
        result.error = f"nano_search_mcp 不可用: {exc}"
        result.error_type = "module_missing"
        result.missing_inputs.append("🔴 [人工介入] 安装 nano_search_mcp 模块")
        return result

    stockid = stockid_from_ts_code(ts_code)
    try:
        entries = fetch_announcement_list(stockid, start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        result.error = f"fetch_announcement_list 失败: {exc}"
        result.error_type = _classify_mcp_error(exc)
        result.missing_inputs.append(f"手动提供 {ts_code} 在 {start_date}~{end_date} 的公告列表（MCP 失败）")
        return result

    retrieved_at = now_iso()
    kws = [k for k in (keywords or []) if k]
    matched = 0
    for ent in entries:
        title = ent.get("title", "")
        url = ent.get("source_url") or ent.get("url") or ""
        if not title or not url:
            continue
        if kws and not any(kw in title for kw in kws):
            continue
        try:
            result.evidence.append(
                Evidence(
                    source_type=SourceType.PRIMARY,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    excerpt=_truncate(f"{ent.get('ann_date', '')} {title}"),
                    title=title,
                )
            )
            matched += 1
            if matched >= limit:
                break
        except ValueError:
            continue

    result.status = "ready" if result.evidence else "partial"
    if not result.evidence and kws:
        result.notes.append(f"在 {len(entries)} 条公告中未匹配关键词 {kws}")
        # 没匹配到不等于不存在，记为 partial + missing_inputs
        result.missing_inputs.append(
            f"{ts_code} 相关公告缺失，关键词 {kws}，请人工补证"
        )
    return result


# ---------------------------------------------------------------------------
# 行业研报（预测）
# ---------------------------------------------------------------------------


def collect_industry_reports(
    ts_code: str,
    *,
    industry_sw_l2: str = "",
    keywords: list[str] | None = None,
    limit: int = 10,
) -> CollectResult:
    result = CollectResult()
    try:
        from nano_search_mcp.tools.industry_reports import fetch_industry_report_list
    except ImportError as exc:
        result.error = f"nano_search_mcp 不可用: {exc}"
        result.error_type = "module_missing"
        result.missing_inputs.append("🔴 [人工介入] 安装 nano_search_mcp 模块")
        return result

    try:
        entries = fetch_industry_report_list(
            industry_sw_l2=industry_sw_l2,
            keywords=keywords,
            limit=limit,
            ts_code=ts_code,
        )
    except Exception as exc:  # noqa: BLE001
        result.error = f"fetch_industry_report_list 失败: {exc}"
        result.error_type = _classify_mcp_error(exc)
        result.missing_inputs.append(f"手动提供 {ts_code} 所属行业研报（MCP 失败）")
        return result

    retrieved_at = now_iso()
    for rep in entries:
        url = rep.get("source_url") or rep.get("url") or ""
        title = rep.get("title", "")
        excerpt = rep.get("summary") or rep.get("abstract") or title
        if not url or not excerpt:
            continue
        try:
            result.evidence.append(
                Evidence(
                    source_type=SourceType.INDUSTRY_REPORT,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    excerpt=_truncate(excerpt),
                    title=title,
                )
            )
        except ValueError:
            continue

    result.status = "ready" if result.evidence else "insufficient-evidence"
    return result


# ---------------------------------------------------------------------------
# IR 会议纪要（公司口径）
# ---------------------------------------------------------------------------


def collect_ir_meetings(
    ts_code: str,
    *,
    start_date: str = "",
    end_date: str = "",
    limit: int = 20,
) -> CollectResult:
    result = CollectResult()
    try:
        from nano_search_mcp.tools.ir_meetings import fetch_ir_meeting_list
    except ImportError as exc:
        result.error = f"nano_search_mcp 不可用: {exc}"
        result.error_type = "module_missing"
        result.missing_inputs.append("🔴 [人工介入] 安装 nano_search_mcp 模块")
        return result

    stockid = stockid_from_ts_code(ts_code)
    try:
        entries = fetch_ir_meeting_list(stockid, start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        result.error = f"fetch_ir_meeting_list 失败: {exc}"
        result.error_type = _classify_mcp_error(exc)
        result.missing_inputs.append(
            f"手动提供 {ts_code} IR/调研/业绩说明会纪要（MCP 失败）"
        )
        return result

    retrieved_at = now_iso()
    for ent in entries[:limit]:
        url = ent.get("source_url") or ent.get("url") or ""
        title = ent.get("title", "")
        if not url or not title:
            continue
        try:
            result.evidence.append(
                Evidence(
                    source_type=SourceType.IR_MEETING,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    excerpt=_truncate(
                        f"{ent.get('ann_date', '')} [{ent.get('meeting_type', '')}] {title}"
                    ),
                    title=title,
                )
            )
        except ValueError:
            continue

    result.status = "ready" if result.evidence else "insufficient-evidence"
    return result


# ---------------------------------------------------------------------------
# 监管处罚
# ---------------------------------------------------------------------------


def collect_penalties(
    ts_code: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> CollectResult:
    result = CollectResult()
    try:
        from nano_search_mcp.tools.regulatory_penalties import fetch_penalty_list
    except ImportError as exc:
        result.error = f"nano_search_mcp 不可用: {exc}"
        result.error_type = "module_missing"
        result.missing_inputs.append("🔴 [人工介入] 安装 nano_search_mcp 模块")
        return result

    try:
        data = fetch_penalty_list(ts_code, start_date=start_date, end_date=end_date)
    except Exception as exc:  # noqa: BLE001
        result.error = f"fetch_penalty_list 失败: {exc}"
        result.error_type = _classify_mcp_error(exc)
        result.missing_inputs.append(f"手动确认 {ts_code} 是否存在监管处罚记录（MCP 失败）")
        return result

    # 该工具的失败是 data.source == "unavailable"——接口永久下线
    if data.get("source") == "unavailable":
        result.error = data.get("error", "penalty source unavailable")
        result.error_type = "source_disabled"
        result.missing_inputs.append(
            f"🔴 [人工介入] 监管处罚源不可用，请手动在 cninfo/sse/szse 核查 {ts_code} 处罚记录"
        )
        return result

    retrieved_at = now_iso()
    for pen in data.get("penalties", []):
        url = pen.get("source_url", "")
        title = pen.get("title", "")
        excerpt_parts = [
            pen.get("punish_date", ""),
            pen.get("event_type", ""),
            title,
            pen.get("reason", ""),
            pen.get("content", ""),
        ]
        excerpt = " | ".join(p for p in excerpt_parts if p)
        if not url or not excerpt:
            continue
        try:
            result.evidence.append(
                Evidence(
                    source_type=SourceType.REGULATORY,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    excerpt=_truncate(excerpt),
                    title=title,
                )
            )
        except ValueError:
            continue

    # 没有处罚记录 = 好事，但要作为证据登记（用列表页 URL）
    if not result.evidence:
        result.status = "ready"  # 明确"无处罚"是事实
        result.notes = ["未发现监管处罚记录（source=sina/vGP_GetOutOfLine）"]
    else:
        result.status = "ready"
    return result


# ---------------------------------------------------------------------------
# 行业政策（gov.cn）
# ---------------------------------------------------------------------------


def collect_industry_policies(
    industry_sw_l2: str,
    *,
    keywords: list[str] | None = None,
) -> CollectResult:
    result = CollectResult()
    if not industry_sw_l2:
        result.missing_inputs.append("industry_sw_l2 缺失，无法检索行业政策")
        return result

    # 硬拦截：缺 DASHSCOPE_API_KEY 就别等 MCP 重试 3 次
    ok, reason = check_bailian_env()
    if not ok:
        result.error = reason
        result.error_type = "env_missing"
        result.missing_inputs.append(
            f"🔴 [人工介入] {reason}"
        )
        return result

    try:
        from nano_search_mcp.tools.industry_policies import fetch_industry_policy_list
    except ImportError as exc:
        result.error = f"nano_search_mcp 不可用: {exc}"
        result.error_type = "module_missing"
        result.missing_inputs.append("🔴 [人工介入] nano_search_mcp 未安装，无法检索行业政策")
        return result

    try:
        entries = fetch_industry_policy_list(
            industry_sw_l2=industry_sw_l2, keywords=keywords
        )
    except Exception as exc:  # noqa: BLE001
        result.error = f"fetch_industry_policy_list 失败: {exc}"
        result.error_type = _classify_mcp_error(exc)
        if result.error_type == "env_missing":
            result.missing_inputs.append(
                f"🔴 [人工介入] {exc}"
            )
        else:
            result.missing_inputs.append(
                f"手动补充 {industry_sw_l2} 行业政策文件（MCP 调用失败）"
            )
        return result

    retrieved_at = now_iso()
    for ent in entries:
        url = ent.get("source_url") or ent.get("url") or ""
        title = ent.get("title", "")
        excerpt = ent.get("snippet") or ent.get("summary") or title
        if not url or not excerpt:
            continue
        try:
            result.evidence.append(
                Evidence(
                    source_type=SourceType.REGULATORY,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    excerpt=_truncate(excerpt),
                    title=title,
                )
            )
        except ValueError:
            continue

    result.status = "ready" if result.evidence else "insufficient-evidence"
    return result
