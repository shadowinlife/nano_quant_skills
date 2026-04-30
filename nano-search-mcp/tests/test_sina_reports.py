import inspect

import pytest

from nano_search_mcp.tools import sina_reports


class DummyMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


def _get_company_report_tool():
    mcp = DummyMCP()
    sina_reports.register_sina_report_tools(mcp)
    return mcp.tools["get_company_report"]


def test_get_company_report_requires_explicit_year_parameter():
    tool = _get_company_report_tool()
    signature = inspect.signature(tool)

    assert list(signature.parameters) == ["stockid", "year", "report_type"]
    assert signature.parameters["report_type"].default == "annual"


def test_get_company_report_defaults_to_requested_year_annual_report(monkeypatch):
    tool = _get_company_report_tool()
    requested_report_types: list[str] = []
    selected_report_ids: list[str] = []

    monkeypatch.setattr(
        sina_reports,
        "fetch_report_listing",
        lambda stockid, report_type: requested_report_types.append(report_type) or {
            "listing_url": "http://example.com/listing",
            "reports": [
                {
                    "date": "2025-04-10",
                    "title": "2024年年度报告",
                    "id": "r-2024",
                    "url": "http://example.com/2024",
                },
                {
                    "date": "2024-04-09",
                    "title": "2023年年度报告摘要",
                    "id": "r-2023-summary",
                    "url": "http://example.com/2023-summary",
                },
                {
                    "date": "2024-04-08",
                    "title": "2023年年度报告（英文版）",
                    "id": "r-2023-en",
                    "url": "http://example.com/2023-en",
                },
                {
                    "date": "2024-04-07",
                    "title": "2023年年度报告",
                    "id": "r-2023",
                    "url": "http://example.com/2023",
                },
            ],
        },
    )

    def _fake_fetch_report_content(stockid: str, report_id: str) -> str:
        selected_report_ids.append(report_id)
        return "\n\n目标年报正文\n\n"

    monkeypatch.setattr(
        sina_reports,
        "fetch_report_content",
        _fake_fetch_report_content,
    )

    result = tool("600519", 2023)

    assert requested_report_types == ["annual"]
    assert selected_report_ids == ["r-2023"]
    assert "【2023年年度报告】" in result
    assert "目标年报正文" in result
    assert "2024年年度报告" not in result


@pytest.mark.parametrize(
    ("report_type_input", "expected_report_type", "target_title", "report_id", "body"),
    [
        ("q1", "q1", "2023年第一季度报告", "r-q1", "目标一季报正文"),
        ("半年报", "semi", "2023年半年度报告", "r-semi", "目标半年报正文"),
        ("三季度报告", "q3", "2023年第三季度报告", "r-q3", "目标三季报正文"),
    ],
)
def test_get_company_report_returns_requested_periodic_report(
    monkeypatch,
    report_type_input,
    expected_report_type,
    target_title,
    report_id,
    body,
):
    tool = _get_company_report_tool()
    requested_report_types: list[str] = []
    selected_report_ids: list[str] = []

    monkeypatch.setattr(
        sina_reports,
        "fetch_report_listing",
        lambda stockid, report_type: requested_report_types.append(report_type) or {
            "listing_url": "http://example.com/listing",
            "reports": [
                {
                    "date": "2025-04-10",
                    "title": target_title.replace("2023", "2024"),
                    "id": report_id + "-2024",
                    "url": "http://example.com/2024",
                },
                {
                    "date": "2024-04-09",
                    "title": target_title + "摘要",
                    "id": report_id + "-summary",
                    "url": "http://example.com/summary",
                },
                {
                    "date": "2024-04-08",
                    "title": target_title + "（英文版）",
                    "id": report_id + "-en",
                    "url": "http://example.com/en",
                },
                {
                    "date": "2024-04-07",
                    "title": target_title,
                    "id": report_id,
                    "url": "http://example.com/2023",
                }
            ],
        },
    )

    def _fake_fetch_report_content(stockid: str, current_report_id: str) -> str:
        selected_report_ids.append(current_report_id)
        return f"\n\n{body}\n\n"

    monkeypatch.setattr(
        sina_reports,
        "fetch_report_content",
        _fake_fetch_report_content,
    )

    result = tool("600519", 2023, report_type_input)

    assert requested_report_types == [expected_report_type]
    assert selected_report_ids == [report_id]
    assert f"【{target_title}】" in result
    assert body in result


def test_get_company_report_rejects_unsupported_report_type():
    tool = _get_company_report_tool()

    with pytest.raises(ValueError, match=r"不支持的报告类型"):
        tool("600519", 2023, "q2")


def test_get_company_report_raises_clear_error_when_report_not_found(monkeypatch):
    tool = _get_company_report_tool()

    monkeypatch.setattr(
        sina_reports,
        "fetch_report_listing",
        lambda stockid, report_type: {
            "listing_url": "http://example.com/listing",
            "reports": [
                {
                    "date": "2025-04-10",
                    "title": "2024年第三季度报告",
                    "id": "r-q3-2024",
                    "url": "http://example.com/2024",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match=r"未找到股票 600519 在 2023 年的三季报"):
        tool("600519", 2023, "q3")


@pytest.mark.parametrize(
    "bad_stockid",
    ["abc", "12345", "1234567", "600519'", "../etc", ""],
)
def test_get_company_report_rejects_invalid_stockid(bad_stockid):
    tool = _get_company_report_tool()

    with pytest.raises(ValueError, match=r"stockid 必须是 6 位数字"):
        tool(bad_stockid, 2023)


def test_build_listing_url_uses_https_and_validates_stockid():
    url = sina_reports.build_listing_url("600519", "annual")
    assert url.startswith("https://vip.stock.finance.sina.com.cn/")
    assert "600519" in url

    with pytest.raises(ValueError):
        sina_reports.build_listing_url("bad-id", "annual")


def test_fetch_report_content_prefers_pdf_notes(monkeypatch):
    monkeypatch.setattr(
        sina_reports,
        "_http_get_gbk",
        lambda url: (
            '<html><body>'
            '<a href="http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2025/2025-8/2025-08-29/11407825.PDF" target="_blank">下载公告</a>'
            '</body></html>'
        ),
    )
    monkeypatch.setattr(sina_reports, "_http_get_binary", lambda url: b"%PDF-1.4")
    monkeypatch.setattr(
        sina_reports,
        "_extract_pdf_text",
        lambda data: "第一部分\n财务报表附注\n注释内容",
    )
    monkeypatch.setattr(
        sina_reports,
        "_extract_notes_text_from_pdf",
        lambda text: "财务报表附注\n注释内容",
    )
    monkeypatch.setattr(sina_reports, "_extract_detail_text", lambda html: "HTML正文")

    result = sina_reports.fetch_report_content("600519", "123456")

    assert "【PDF来源】" in result
    assert "【附注节选】" in result
    assert "注释内容" in result
    assert "HTML正文" not in result


def test_fetch_report_content_falls_back_to_html_when_pdf_fails(monkeypatch):
    monkeypatch.setattr(
        sina_reports,
        "_http_get_gbk",
        lambda url: (
            '<html><body>'
            '<a href="http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2025/2025-8/2025-08-29/11407825.PDF" target="_blank">下载公告</a>'
            '</body></html>'
        ),
    )

    def _raise_pdf_error(url: str) -> bytes:
        raise RuntimeError("pdf error")

    monkeypatch.setattr(sina_reports, "_http_get_binary", _raise_pdf_error)
    monkeypatch.setattr(sina_reports, "_extract_detail_text", lambda html: "HTML正文")

    result = sina_reports.fetch_report_content("600519", "123456")

    assert result == "HTML正文"


def test_find_pdf_url_in_detail_html_prefers_download_notice_link():
    """优先匹配链接文本为「下载公告」的 file.finance.sina.com.cn 链接。"""
    real_pdf_url = (
        "http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2025/2025-8/2025-08-29/11407825.PDF"
    )
    html = (
        '<html><body>'
        f'<a href="{real_pdf_url}" target="_blank">下载公告</a>'
        '</body></html>'
    )

    result = sina_reports._find_pdf_url_in_detail_html(
        html,
        "https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?stockid=600519&id=123",
    )

    assert result == real_pdf_url


def test_find_pdf_url_in_detail_html_rejects_untrusted_domain():
    html = (
        '<html><body>'
        '<a href="https://evil.example.com/annual.pdf">下载公告</a>'
        '<a href="http://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2025/2025-8/2025-08-29/11407825.PDF" target="_blank">下载公告</a>'
        "</body></html>"
    )

    result = sina_reports._find_pdf_url_in_detail_html(
        html,
        "https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?stockid=600519&id=123",
    )

    assert "evil.example.com" not in (result or "")
    assert result is not None
    assert "file.finance.sina.com.cn" in result


def test_get_company_report_prefers_listing_pdf_url(monkeypatch):
    tool = _get_company_report_tool()

    monkeypatch.setattr(
        sina_reports,
        "fetch_report_listing",
        lambda stockid, report_type: {
            "listing_url": "http://example.com/listing",
            "reports": [
                {
                    "date": "2024-04-07",
                    "title": "2023年年度报告",
                    "id": "r-2023",
                    "url": "http://example.com/2023",
                    "pdf_url": "https://vip.stock.finance.sina.com.cn/files/2023.pdf",
                }
            ],
        },
    )
    monkeypatch.setattr(
        sina_reports,
        "_extract_content_from_pdf_url",
        lambda pdf_url: "【PDF来源】x\n\n【附注节选】\n附注内容",
    )

    def _should_not_be_called(stockid: str, report_id: str) -> str:
        raise AssertionError("should not call detail fallback")

    monkeypatch.setattr(sina_reports, "fetch_report_content", _should_not_be_called)

    result = tool("600519", 2023, "annual")

    assert "附注内容" in result
