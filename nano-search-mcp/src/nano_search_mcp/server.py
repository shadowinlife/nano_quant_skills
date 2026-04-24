"""NanoSearch MCP Server - 主服务模块"""

import argparse
from collections.abc import Sequence

from mcp.server.fastmcp import FastMCP

from nano_search_mcp.tools.announcements import register_announcement_tools
from nano_search_mcp.tools.deferred_search import register_deferred_search_tools
from nano_search_mcp.tools.fetch import register_fetch_tools
from nano_search_mcp.tools.industry_policies import register_industry_policy_tools
from nano_search_mcp.tools.industry_reports import register_industry_report_tools
from nano_search_mcp.tools.ir_meetings import register_ir_meeting_tools
from nano_search_mcp.tools.regulatory_penalties import register_regulatory_penalty_tools
from nano_search_mcp.tools.search import register_search_tools
from nano_search_mcp.tools.sina_reports import register_sina_report_tools

# 创建 MCP 服务实例
mcp = FastMCP(
    name="NanoSearch",
    streamable_http_path="/mcp",
    instructions=(
        "NanoSearch 是面向中国 A 股市场的结构化文本检索服务，按能力域提供以下 MCP 工具：\n"
        "\n"
        "【通用检索】\n"
        "- search: 百炼 WebSearch 网页搜索，返回 [{title, url, snippet}] 列表\n"
        "- fetch_page: 抓取任意 URL 正文（Markdown 格式），当前使用 Playwright\n"
        "- search_deferred_topic: 基于命名模板或自由查询的百炼 WebSearch 检索，"
        "支持通过 context 变量填充模板参数\n"
        "\n"
        "【定期报告】\n"
        "- get_company_report: 获取指定 A 股公司指定年份的年报/半年报/一季报/三季报全文正文；"
        "调用方必须显式提供 year 与 report_type（默认 annual）\n"
        "\n"
        "【临时公告】\n"
        "- list_announcements: 列出指定公司临时公告条目（支持 ann_type 过滤）\n"
        "- get_announcement_text: 抓取单条公告正文\n"
        "\n"
        "【行业研报】\n"
        "- list_industry_reports: 列出行业研究报告（可通过 ts_code 自动路由至申万二级行业，"
        "或直接指定 industry_sw_l2 + 关键词；默认返回近 1 年数据）\n"
        "- get_report_text: 抓取单条行业研报正文\n"
        "\n"
        "【监管与处罚】\n"
        "- list_regulatory_penalties: 列出指定公司监管处罚 / 违规处理记录\n"
        "\n"
        "【投资者关系】\n"
        "- list_ir_meetings: 列出机构调研记录、业绩说明会等投资者关系活动\n"
        "- get_ir_meeting_text: 抓取单条 IR 纪要正文及参会机构名单\n"
        "\n"
        "【行业政策】\n"
        "- list_industry_policies: 检索政府机构（*.gov.cn）近 1 年内发布的行业政策文件，"
        "最多返回 5 条\n"
        "\n"
        "错误契约：除 search 与 get_company_report 在参数非法或网络彻底失败时抛出异常外，"
        "其余工具在失败时返回 {source: \"unavailable\", error, fetch_time}，不抛异常。"
    ),
)

# 注册工具
register_search_tools(mcp)
register_fetch_tools(mcp)
register_sina_report_tools(mcp)
register_deferred_search_tools(mcp)
register_announcement_tools(mcp)
register_industry_report_tools(mcp)
register_regulatory_penalty_tools(mcp)
register_ir_meeting_tools(mcp)
register_industry_policy_tools(mcp)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动 NanoSearch MCP server")
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "stdio"),
        default="streamable-http",
        help="选择 MCP transport；默认 streamable-http，本地直连可用 stdio",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """启动 MCP Server，默认 streamable HTTP，可通过参数切换到 stdio。"""
    args = _build_parser().parse_args(list(argv) if argv is not None else [])
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
