"""兼容性 HTTP 入口，复用标准 MCP streamable HTTP 服务。"""

from nano_search_mcp.server import main as _server_main
from nano_search_mcp.server import mcp

app = mcp.streamable_http_app()


def main() -> None:
    """兼容旧入口；实际启动标准 MCP streamable HTTP 服务。"""
    _server_main()
