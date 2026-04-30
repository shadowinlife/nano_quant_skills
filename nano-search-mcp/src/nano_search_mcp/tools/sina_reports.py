"""新浪财经定期报告直接抓取工具

URL 规律（无需搜索，直接拼接）：

  列表页：https://vip.stock.finance.sina.com.cn/corp/go.php/{view}/stockid/{stockid}/page_type/{page_type}.phtml
  详情页：https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?stockid={stockid}&id={id}

page_type 与 view 的对应关系（固定，由页面导航链接确认）：
  年度报告   → vCB_Bulletin      / ndbg
  中期报告   → vCB_BulletinZhong / zqbg
  一季度报告 → vCB_BulletinYi    / yjdbg
  三季度报告 → vCB_BulletinSan   / sjdbg
"""

from __future__ import annotations

import io
import logging
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

from nano_search_mcp.config import get_settings

logger = logging.getLogger(__name__)

# 优先 https，若握手失败再回退 http
_BASE_HTTPS = "https://vip.stock.finance.sina.com.cn"
_BASE_HTTP = "http://vip.stock.finance.sina.com.cn"
_DETAIL_PATH_TPL = "/corp/view/vCB_AllBulletinDetail.php?stockid={stockid}&id={id}"
_LIST_PATH_TPL = "/corp/go.php/{view}/stockid/{stockid}/page_type/{page_type}.phtml"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 校验 stockid 为 6 位数字，防止 URL 注入 / SSRF
_STOCKID_PATTERN = re.compile(r"^\d{6}$")
# 校验 report id 为纯数字
_REPORT_ID_PATTERN = re.compile(r"^\d+$")

# 报告类型别名 → (view, page_type)
ReportType = Literal["annual", "semi", "q1", "q3"]

_REPORT_TYPE_MAP: dict[str, tuple[str, str]] = {
    "annual": ("vCB_Bulletin",      "ndbg"),
    "semi":   ("vCB_BulletinZhong", "zqbg"),
    "q1":     ("vCB_BulletinYi",    "yjdbg"),
    "q3":     ("vCB_BulletinSan",   "sjdbg"),
}

_CN_ALIAS: dict[str, str] = {
    "年报": "annual", "年度报告": "annual",
    "半年报": "semi", "中报": "semi", "中期报告": "semi",
    "一季报": "q1", "一季度报告": "q1",
    "三季报": "q3", "三季度报告": "q3",
}

_REPORT_TYPE_LABELS: dict[str, str] = {
    "annual": "年报",
    "semi": "半年报",
    "q1": "一季报",
    "q3": "三季报",
}

_REPORT_TITLE_PATTERNS: dict[str, str] = {
    "annual": r"(年度报告|年报)",
    "semi": r"(半年度报告|半年报|中期报告|中报)",
    "q1": r"(第一季度报告|一季度报告|一季报)",
    "q3": r"(第三季度报告|三季度报告|三季报)",
}

_ALLOWED_PDF_HOST_SUFFIXES = (".sina.com.cn", ".sinaimg.cn")
# 「下载公告」按钮固定域名（file.finance.sina.com.cn 经 IP 直连）
_ALLOWED_PDF_HOSTS = frozenset([
    "vip.stock.finance.sina.com.cn",
    "file.finance.sina.com.cn",
])


def _validate_stockid(stockid: str) -> str:
    """校验股票代码为 6 位数字，避免 URL 注入 / SSRF。"""
    if not isinstance(stockid, str) or not _STOCKID_PATTERN.fullmatch(stockid):
        raise ValueError(f"stockid 必须是 6 位数字字符串，收到: {stockid!r}")
    return stockid


def _validate_report_id(report_id: str) -> str:
    if not isinstance(report_id, str) or not _REPORT_ID_PATTERN.fullmatch(report_id):
        raise ValueError(f"report id 必须是纯数字字符串，收到: {report_id!r}")
    return report_id


def resolve_report_type(report_type: str) -> str:
    """将中文别名或英文 key 统一为内部英文 key。"""
    key = report_type.strip()
    if key in _REPORT_TYPE_MAP:
        return key
    resolved = _CN_ALIAS.get(key)
    if resolved is None:
        valid = list(_REPORT_TYPE_MAP) + list(_CN_ALIAS)
        raise ValueError(f"不支持的报告类型 {key!r}，可选：{valid}")
    return resolved


def build_listing_url(stockid: str, report_type: str) -> str:
    """根据股票代码和报告类型拼接列表页 URL，无需任何网络请求。"""
    _validate_stockid(stockid)
    key = resolve_report_type(report_type)
    view, page_type = _REPORT_TYPE_MAP[key]
    return _BASE_HTTPS + _LIST_PATH_TPL.format(view=view, stockid=stockid, page_type=page_type)


def _build_detail_url(stockid: str, report_id: str, *, base: str = _BASE_HTTPS) -> str:
    _validate_stockid(stockid)
    _validate_report_id(report_id)
    return base + _DETAIL_PATH_TPL.format(stockid=stockid, id=report_id)


def _http_get_gbk(url: str, timeout: int = 15) -> str:
    """抓取 GBK 编码页面，返回解码后的 HTML 字符串。

    - 优先使用传入 URL（https）；若 https 握手/连接失败则回退 http。
    - 网络/HTTP 错误使用指数退避重试（支持配置 `http.max_retries`）。
    - 仅允许 sina 目标域，避免 SSRF。
    """
    if not (url.startswith(_BASE_HTTPS) or url.startswith(_BASE_HTTP)):
        raise ValueError(f"禁止访问非新浪财经域名: {url}")

    cfg = get_settings()
    last_error: Exception | None = None
    for attempt in range(cfg.http.max_retries):
        if attempt > 0:
            backoff = cfg.http.backoff_base ** attempt + random.uniform(0.2, 0.8)
            logger.warning(
                "[sina_reports] 抓取失败，第 %d 次重试，退避 %.1fs: %s",
                attempt, backoff, url,
            )
            time.sleep(backoff)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            return raw.decode("gbk", errors="replace")
        except urllib.error.URLError as exc:
            last_error = exc
            # https 握手失败 → 回退 http（仅第一次）
            if attempt == 0 and url.startswith(_BASE_HTTPS):
                fallback = _BASE_HTTP + url[len(_BASE_HTTPS):]
                logger.warning("[sina_reports] https 失败，回退 http: %s", fallback)
                url = fallback
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise RuntimeError(
        f"抓取新浪财经页面失败，已重试 {cfg.http.max_retries} 次: {url}。最后错误: {last_error}"
    ) from last_error


def _http_get_binary(url: str, timeout: int = 30) -> bytes:
    """抓取二进制内容（用于 PDF），支持重试。"""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"仅允许 http/https PDF 链接: {url}")

    cfg = get_settings()
    last_error: Exception | None = None
    for attempt in range(cfg.http.max_retries):
        if attempt > 0:
            backoff = cfg.http.backoff_base ** attempt + random.uniform(0.2, 0.8)
            logger.warning(
                "[sina_reports] PDF 抓取失败，第 %d 次重试，退避 %.1fs: %s",
                attempt,
                backoff,
                url,
            )
            time.sleep(backoff)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise RuntimeError(
        f"抓取 PDF 失败，已重试 {cfg.http.max_retries} 次: {url}。最后错误: {last_error}"
    ) from last_error


def _is_allowed_pdf_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return host in _ALLOWED_PDF_HOSTS or any(
        host.endswith(suffix) for suffix in _ALLOWED_PDF_HOST_SUFFIXES
    )


def _find_pdf_url_in_detail_html(html: str, detail_url: str) -> str | None:
    """从详情页中提取「下载公告」PDF 链接。

    优先精确匹配链接文本为「下载公告」的 <a> 标签（新浪财经定期报告页面固定样式）；
    若未命中则回退到任意 .pdf 链接（兼容页面改版）。
    仅信任白名单域名，防止 SSRF。
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        if not href:
            continue
        full_url = urllib.parse.urljoin(detail_url, href)
        if not _is_allowed_pdf_url(full_url):
            continue
        link_text = a.get_text(separator=" ", strip=True)
        # 精确匹配：文字为「下载公告」
        if link_text == "下载公告":
            return full_url
        # 保留作备用
        if ".pdf" in full_url.lower() or "pdf" in link_text.lower():
            candidates.append(full_url)
    return candidates[0] if candidates else None


def _extract_pdf_text(pdf_bytes: bytes, max_pages: int = 120) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    chunks: list[str] = []
    for idx, page in enumerate(reader.pages):
        if idx >= max_pages:
            break
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text)
    return "\n\n".join(chunks).strip()


def _extract_notes_text_from_pdf(full_text: str) -> str | None:
    """从 PDF 文本中抽取“财务报表附注”等重点段落。"""
    if not full_text.strip():
        return None

    normalized = re.sub(r"\r\n?", "\n", full_text)
    lines = [line.strip() for line in normalized.split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return None

    start_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r"(财务报表|会计报表).{0,8}附注", line):
            start_idx = idx
            break
        if re.fullmatch(r"(附注|报表附注)", line):
            start_idx = idx
            break

    if start_idx == -1:
        hit_indices = [
            idx for idx, line in enumerate(lines)
            if "附注" in line and "目录" not in line and len(line) <= 120
        ]
        if not hit_indices:
            return None
        snippets: list[str] = []
        for idx in hit_indices[:20]:
            left = max(0, idx - 1)
            right = min(len(lines), idx + 2)
            snippets.append("\n".join(lines[left:right]))
        return "\n\n".join(snippets).strip() or None

    end_idx = len(lines)
    for idx in range(start_idx + 20, len(lines)):
        line = lines[idx]
        if re.match(r"^第[一二三四五六七八九十百]+节", line):
            end_idx = idx
            break

    notes_lines = lines[start_idx:end_idx]
    notes_text = "\n".join(notes_lines).strip()
    if len(notes_text) > 30000:
        notes_text = notes_text[:30000]
    return notes_text or None


def _extract_content_from_pdf_url(pdf_url: str) -> str | None:
    """下载并解析 PDF，优先返回附注段落。"""
    if not _is_allowed_pdf_url(pdf_url):
        raise ValueError(f"不允许的 PDF 域名: {pdf_url}")
    pdf_bytes = _http_get_binary(pdf_url)
    pdf_text = _extract_pdf_text(pdf_bytes)
    notes_text = _extract_notes_text_from_pdf(pdf_text)
    if notes_text:
        return f"【PDF来源】{pdf_url}\n\n【附注节选】\n{notes_text}"
    if pdf_text:
        return f"【PDF来源】{pdf_url}\n\n{pdf_text}"
    return None


def _extract_listing(html: str, stockid: str) -> list[dict[str, str]]:
    """解析列表页 HTML，提取报告条目（date, title, id, url）。"""
    soup = BeautifulSoup(html, "html.parser")
    entries: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for a in soup.find_all("a", href=re.compile(r"vCB_AllBulletinDetail")):
        href_value = a.get("href")
        if not isinstance(href_value, str):
            continue
        href = href_value
        id_match = re.search(r"[?&]id=(\d+)", href)
        if not id_match:
            continue
        report_id = id_match.group(1)
        if report_id in seen_ids:
            continue
        seen_ids.add(report_id)

        title = a.get_text(strip=True)
        parent = a.parent

        # 优先从 <a> 的前序文本节点提取日期（新浪列表页结构：日期文本&nbsp;<a>标题</a><br>...）
        date = ""
        prev = a.previous_sibling
        if prev is not None:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", str(prev))
            if date_match:
                date = date_match.group(1)
        # 兜底：从父节点完整文本中搜索（兼容其他页面结构）
        if not date:
            parent_text = parent.get_text(separator=" ", strip=True) if parent else ""
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", parent_text)
            date = date_match.group(1) if date_match else ""

        pdf_url = ""
        if parent:
            # 优先：链接文字为「下载公告」（新浪定期报告列表页固定样式）
            fallback_pdf: str = ""
            for sibling_link in parent.find_all("a", href=True):
                sibling_href = str(sibling_link.get("href") or "").strip()
                if not sibling_href:
                    continue
                # href 可能是绝对 URL（含 IP:port），直接使用；相对路径才拼接
                if sibling_href.startswith(("http://", "https://")):
                    candidate = sibling_href
                else:
                    candidate = urllib.parse.urljoin(_BASE_HTTPS, sibling_href)
                if not _is_allowed_pdf_url(candidate):
                    continue
                sibling_text = sibling_link.get_text(separator=" ", strip=True)
                if sibling_text == "下载公告":
                    pdf_url = candidate
                    break
                if ".pdf" in candidate.lower() and not fallback_pdf:
                    fallback_pdf = candidate
            if not pdf_url:
                pdf_url = fallback_pdf

        # 规范化 URL：始终指向经校验的 sina 详情页
        full_url = _build_detail_url(stockid, report_id)

        entries.append({
            "date": date,
            "title": title,
            "id": report_id,
            "url": full_url,
            "pdf_url": pdf_url,
        })

    return entries


def _extract_detail_text(html: str) -> str:
    """从详情页 HTML 提取公告正文纯文本。

    选择器优先级：
      1. div#con02-7.tagmain —— 新浪财经详情页正文容器（已验证）
      2. div#allbulletin      —— 旧版/备用容器
      3. body                 —— 最终兜底
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(id="con02-7")
    if not container:
        container = soup.find(id="allbulletin")
    if not container:
        container = soup.find("body") or soup
    return container.get_text(separator="\n", strip=True)  # type: ignore[union-attr]


def _validate_report_year(year: int) -> int:
    """校验调用方输入的报告年份。"""
    if not 1900 <= year <= 2100:
        raise ValueError("year 必须是四位年份，例如 2023。")
    return year


def _report_type_label(report_type: str) -> str:
    """返回规范化报告类型对应的中文名称。"""
    key = resolve_report_type(report_type)
    return _REPORT_TYPE_LABELS[key]


def _is_target_report(title: str, year: int, report_type: str) -> bool:
    """判断标题是否对应目标年份的指定定期报告。"""
    key = resolve_report_type(report_type)
    if not re.search(_REPORT_TITLE_PATTERNS[key], title):
        return False
    return re.search(rf"(?<!\d){year}\s*年", title) is not None


def _select_report_for_year(
    reports: list[dict[str, str]],
    stockid: str,
    year: int,
    report_type: str,
) -> dict[str, str]:
    """从指定报告列表中选出目标年份的一份正文报告。"""
    label = _report_type_label(report_type)
    for report in reports:
        if _is_target_report(report["title"], year, report_type):
            return report

    raise ValueError(
        f"未找到股票 {stockid} 在 {year} 年的{label}，请确认股票代码、年份和报告类型是否正确。"
    )


def fetch_report_listing(stockid: str, report_type: str) -> dict:
    """获取某只股票某类报告的列表。"""
    listing_url = build_listing_url(stockid, report_type)
    logger.info("[sina_reports] 抓取列表页: %s", listing_url)
    html = _http_get_gbk(listing_url)
    reports = _extract_listing(html, stockid)
    logger.info("[sina_reports] 找到 %d 条报告", len(reports))
    return {"listing_url": listing_url, "reports": reports}


def fetch_report_content(stockid: str, report_id: str) -> str:
    """抓取单份报告正文，优先解析 PDF 并提取附注。"""
    url = _build_detail_url(stockid, report_id)
    logger.info("[sina_reports] 抓取详情页: %s", url)
    html = _http_get_gbk(url)

    pdf_url = _find_pdf_url_in_detail_html(html, url)
    if pdf_url:
        logger.info("[sina_reports] 发现 PDF 链接: %s", pdf_url)
        try:
            pdf_content = _extract_content_from_pdf_url(pdf_url)
            if pdf_content:
                return pdf_content
        except Exception as exc:  # noqa: BLE001
            logger.warning("[sina_reports] PDF 解析失败，回退 HTML 正文: %s", exc)

    return _extract_detail_text(html)


def fetch_reports(
    stockid: str,
    report_type: str,
    *,
    limit: int = 5,
    fetch_content: bool = False,
    exclude_english: bool = True,
    exclude_summary: bool = True,
) -> dict:
    """一步获取报告列表，可选同时拉取正文。"""
    key = resolve_report_type(report_type)
    listing = fetch_report_listing(stockid, key)
    reports = listing["reports"]

    if exclude_english:
        reports = [r for r in reports if "英文" not in r["title"]]
    if exclude_summary:
        reports = [r for r in reports if "摘要" not in r["title"]]

    reports = reports[:limit]

    if fetch_content:
        for r in reports:
            try:
                r["content"] = fetch_report_content(stockid, r["id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("[sina_reports] 详情页抓取失败 id=%s: %s", r["id"], exc)
                r["content"] = None
    else:
        for r in reports:
            r["content"] = None

    return {
        "stockid": stockid,
        "report_type": key,
        "listing_url": listing["listing_url"],
        "reports": reports,
    }


def _clean_report_text(text: str) -> str:
    """压缩正文中连续空行，去除首尾空白，减少冗余换行。"""
    # 将连续 3 个以上空行压缩为 2 个
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def register_sina_report_tools(mcp: FastMCP) -> None:
    """注册新浪财经定期报告抓取 MCP Tools。"""

    @mcp.tool()
    def get_company_report(
        stockid: str,
        year: int,
        report_type: str = "annual",
    ) -> str:
        """获取 A 股上市公司指定年份定期报告的全文正文。

        调用方必须显式提供 year；不支持“最近一期”“最新报告”这类含糊调用。
        report_type 默认为 annual（年报）；semi 表示半年报/中报，q1 表示一季报，q3 表示三季报，也支持这些中文别名。
        工具只返回目标年份的一份中文完整版定期报告；若该年份不存在数据则直接报错。

        Args:
            stockid: 股票代码，6 位数字字符串，不含交易所前缀。
                例如 "600519"（贵州茅台）、"000858"（五粮液）、"601318"（中国平安）。
            year: 报告所属年份，例如 2023。这里指“2023 年报”或“2023 年一季报”的所属年份，不是发布日期年份。
            report_type: 报告类型，默认 annual（年报）。
                semi 表示半年报/中报，q1 表示一季报，q3 表示三季报；也支持对应中文别名。

        Returns:
            目标年份指定定期报告的正文全文。正文前附带标题、发布日期与来源链接。

        Raises:
            ValueError: stockid 非法、year 非法、report_type 非法，或找不到该年份报告。
            RuntimeError: 找到了目标报告，但正文抓取失败。
        """
        _validate_stockid(stockid)
        year = _validate_report_year(year)
        report_key = resolve_report_type(report_type)
        report_label = _report_type_label(report_key)

        listing = fetch_report_listing(stockid, report_key)
        reports = listing["reports"]

        reports = [r for r in reports if "英文" not in r["title"]]
        reports = [r for r in reports if "摘要" not in r["title"]]
        target_report = _select_report_for_year(reports, stockid, year, report_key)

        header = (
            f"【{target_report['title']}】\n"
            f"发布日期：{target_report['date']}\n"
            f"来源：{target_report['url']}\n"
        )
        try:
            listing_pdf_url = target_report.get("pdf_url")
            content = None
            if isinstance(listing_pdf_url, str) and listing_pdf_url:
                try:
                    logger.info("[sina_reports] 使用列表页 PDF 链接抓取: %s", listing_pdf_url)
                    content = _extract_content_from_pdf_url(listing_pdf_url)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[sina_reports] 列表页 PDF 解析失败，回退详情页: %s", exc)

            if content is None:
                content = fetch_report_content(stockid, target_report["id"])
            content = _clean_report_text(content)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"抓取股票 {stockid} 在 {year} 年的{report_label}正文失败: {exc}"
            ) from exc

        return header + "\n" + content
