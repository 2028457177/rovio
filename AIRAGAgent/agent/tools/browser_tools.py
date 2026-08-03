"""网页抓取与解析工具（SubAgent browser）。

提供 URL 抓取、链接提取、正文智能提取、网页截图能力。
依赖 beautifulsoup4（可选）：存在则用 bs4 解析，不存在则退化为正则实现，
保证模块在任何环境下都能 import 成功。

截图功能依赖 playwright（可选）：首次使用需安装 chromium 浏览器，
工具会自动检测并提示用户通过 install_package 安装。

ContextVar 依赖：无（纯无状态抓取）。
"""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import requests
from langchain_core.tools import tool
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.paths import get_screenshot_dir
from AIRAGAgent.agent.tools.agent_tools import user_id_var
# 触发 sandbox_config 模块加载：它会注入 PLAYWRIGHT_DOWNLOAD_HOST / PLAYWRIGHT_BROWSERS_PATH 环境变量
from AIRAGAgent.agent.tools.sandbox_config import PLAYWRIGHT_MIRROR  # noqa: F401

# 检测 beautifulsoup4 是否可用
try:
    from bs4 import BeautifulSoup  # noqa: F401
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

# 检测 playwright 是否可用
try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

# 完整浏览器请求头：与真实 Chrome 120 一致，避免被"裸请求"反爬识别
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

# 全局共享 Session：跨请求保持 Cookie（先访问首页种 Cookie 再抓目标页的场景自动生效）
_session = requests.Session()
_session.headers.update(_DEFAULT_HEADERS)
# 幂等请求自动重试（503/超时等），退避 0.5s 起
_retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
_session.mount("http://", HTTPAdapter(max_retries=_retry))
_session.mount("https://", HTTPAdapter(max_retries=_retry))


def _human_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """模拟人类访问节奏，随机停顿，避免高频请求触发限流。"""
    time.sleep(random.uniform(min_s, max_s))

# 需要剔除的"非正文"标签
_STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]


def _fetch_html(url: str, timeout: int = 15, referer: str = "") -> str:
    """获取 URL 的 HTML 文本（带随机延迟 + Session 保持 Cookie + 重试）。

    referer 可选：部分站点要求目标页带 Referer 才放行。
    """
    _human_delay()  # 模拟人类访问节奏
    headers = {"Referer": referer} if referer else {}
    resp = _session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    # 优先用响应头声明的编码；requests 在无 charset 时默认 ISO-8859-1，需 fallback
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def _html_to_text(html: str, max_chars: int) -> str:
    """HTML -> 纯文本，优先 bs4，退化正则。"""
    if _HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(_STRIP_TAGS):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    else:
        text = _strip_tags_regex(html)

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n... [已截断，共 {len(text)} 字符]"
    return text or "[空内容] 该网页未提取到正文文本"


def _strip_tags_regex(html: str) -> str:
    """正则版：去掉 script/style/nav/footer 等标签及其内容，再去标签取文本。"""
    for tag in _STRIP_TAGS:
        html = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", html, flags=re.IGNORECASE | re.DOTALL)
    # 去 HTML 注释
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    # 去剩余标签
    text = re.sub(r"<[^>]+>", " ", html)
    # 折叠空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_links_regex(html: str) -> List[Dict[str, str]]:
    """正则版：从 HTML 提取链接列表。"""
    links: List[Dict[str, str]] = []
    pattern = re.compile(
        r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if href:
            links.append({"text": text, "href": href})
    return links


@tool(description="抓取网页并返回纯文本内容。适用于需要读取网页文章、文档、API 说明等场景。自动去除脚本、样式、导航等非正文内容。默认截断到 8000 字符。")
def fetch_url(url: str, max_chars: int = 8000) -> str:
    """抓取网页，返回去除标签后的纯文本。

    Args:
        url: 目标网页 URL（需含 http:// 或 https://）
        max_chars: 返回文本最大字符数，默认 8000
    """
    try:
        html = _fetch_html(url)
    except Exception as e:
        logger.warning(f"[browser] fetch_url 失败 url={url}: {e}")
        hint = "，可尝试 fetch_url_rendered 用真实浏览器渲染" if "403" in str(e) or "Forbidden" in str(e) else ""
        return f"[抓取失败] {type(e).__name__}: {e}{hint}"

    return _html_to_text(html, max_chars)


@tool(description="从网页提取所有超链接列表，返回 JSON 字符串。可用 filter_pattern 正则过滤 href。适用于需要发现页面内相关链接、下载地址、分页等场景。")
def extract_links(url: str, filter_pattern: str = "") -> str:
    """从网页提取链接，返回 JSON 数组 [{text, href}, ...]。

    Args:
        url: 目标网页 URL
        filter_pattern: 可选正则，仅保留 href 匹配该模式的链接；空字符串表示不过滤
    """
    try:
        html = _fetch_html(url)
    except Exception as e:
        logger.warning(f"[browser] extract_links 失败 url={url}: {e}")
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

    if _HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        links: List[Dict[str, str]] = []
        for a in soup.find_all("a", href=True):
            links.append({"text": a.get_text(strip=True), "href": a["href"].strip()})
    else:
        links = _extract_links_regex(html)

    if filter_pattern:
        try:
            pat = re.compile(filter_pattern)
            links = [l for l in links if pat.search(l["href"])]
        except re.error as e:
            return json.dumps({"error": f"filter_pattern 正则非法: {e}"}, ensure_ascii=False)

    return json.dumps(links, ensure_ascii=False)


@tool(description="智能提取网页正文，去除导航/广告/侧边栏。优先取 <article>、<main> 或最长的 <div>。适用于需要读取文章主体的场景。")
def read_page_main_text(url: str) -> str:
    """智能提取网页正文，返回纯文本。

    Args:
        url: 目标网页 URL
    """
    try:
        html = _fetch_html(url)
    except Exception as e:
        logger.warning(f"[browser] read_page_main_text 失败 url={url}: {e}")
        return f"[抓取失败] {type(e).__name__}: {e}"

    if _HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        # 先剔除干扰标签
        for tag in soup(_STRIP_TAGS):
            tag.decompose()
        # 优先 article > main > 最长 div
        candidate = soup.find("article")
        if not candidate or len(candidate.get_text(strip=True)) < 50:
            candidate = soup.find("main")
        if not candidate or len(candidate.get_text(strip=True)) < 50:
            best_div = None
            best_len = 0
            for div in soup.find_all("div"):
                t = div.get_text(strip=True)
                if len(t) > best_len:
                    best_len = len(t)
                    best_div = div
            candidate = best_div
        text = candidate.get_text(separator=" ", strip=True) if candidate else ""
    else:
        # 正则退化：直接取全页去标签文本
        text = _strip_tags_regex(html)

    return text or "[空内容] 未能提取到正文"


# ── 网页截图 / 渲染抓取（Playwright + 反检测） ──

# 注入页面的反检测脚本：抹掉 webdriver 标记、伪装插件/语言/Chrome 环境
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = {runtime: {}};
"""

# 反检测启动参数：禁用 Blink 自动化标记等
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
    "--disable-infobars",
]


def _launch_stealth_browser(headless: bool = True):
    """启动带反检测配置的 Chromium，返回 (playwright, browser, context)。

    用法：p, browser, context = _launch_stealth_browser()
    结束后必须依次 context.close() -> browser.close() -> p.stop()。
    """
    from playwright.sync_api import sync_playwright

    p = sync_playwright().start()
    browser = p.chromium.launch(headless=headless, args=_STEALTH_ARGS)
    context = browser.new_context(
        user_agent=_DEFAULT_HEADERS["User-Agent"],
        viewport={"width": 1366, "height": 768},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    context.add_init_script(_STEALTH_JS)
    return p, browser, context

def _ensure_chromium() -> str:
    """检测 chromium 浏览器是否已安装，未装时返回提示，已装返回空字符串。

    检测策略：优先查 PLAYWRIGHT_BROWSERS_PATH 下的 chromium-* 目录，
    找不到则尝试启动浏览器（更慢但更可靠）。
    """
    if not _HAS_PLAYWRIGHT:
        return (
            "[playwright 未安装] 请先调用 install_package('playwright') 安装 playwright，"
            "然后调用 run_shell_command('playwright install chromium') 下载 chromium 浏览器（约 150MB，已配国内镜像）。"
        )

    # 1. 优先查 PLAYWRIGHT_BROWSERS_PATH 下的 chromium-* 目录
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if browsers_path:
        bp = Path(browsers_path)
        if bp.exists():
            # 找 chromium-XXX 目录
            chrom_dirs = list(bp.glob("chromium-*"))
            if chrom_dirs:
                # 找到 chromium 目录，再确认 chrome.exe / chrome 存在
                for cd in chrom_dirs:
                    if sys.platform == "win32":
                        exe = cd / "chrome-win64" / "chrome.exe"
                    else:
                        exe = cd / "chrome-linux" / "chrome"
                    if exe.exists():
                        return ""  # 已就位
                # 有目录但没 exe，说明下载不完整
                return (
                    "[chromium 下载不完整] 找到 chromium 目录但缺少可执行文件。"
                    "请重新调用 run_shell_command('playwright install chromium') 下载。"
                )
        # PLAYWRIGHT_BROWSERS_PATH 目录不存在或无 chromium-XXX
        return (
            "[chromium 未下载] playwright 已装但 chromium 浏览器未下载。"
            "请调用 run_shell_command('playwright install chromium') 下载（约 150MB，已配国内镜像加速）。"
        )

    # 2. 没设 PLAYWRIGHT_BROWSERS_PATH，回退到启动检测
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg.lower():
            return (
                "[chromium 未下载] playwright 已装但 chromium 浏览器未下载。"
                "请调用 run_shell_command('playwright install chromium') 下载（约 150MB，已配国内镜像加速）。"
            )
        return f"[chromium 检测失败] {type(e).__name__}: {e}"
    return ""


@tool(description="用真实浏览器渲染网页后提取纯文本（带反检测伪装）。适用于数据由 JS 动态渲染、requests 直接抓取拿不到内容或被 403 拦截的页面。自动等待页面渲染完成。")
def fetch_url_rendered(url: str, max_chars: int = 8000, wait_ms: int = 2500, timeout: int = 30) -> str:
    """真实浏览器渲染抓取，返回纯文本。

    Args:
        url: 目标网页 URL（需含 http:// 或 https://）
        max_chars: 返回文本最大字符数，默认 8000
        wait_ms: 页面加载完成后额外等待毫秒数（让 JS 渲染完），默认 2500
        timeout: 页面加载超时秒数，默认 30
    """
    err = _ensure_chromium()
    if err:
        return err

    p = browser = context = None
    try:
        p, browser, context = _launch_stealth_browser()
        page = context.new_page()
        page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
        page.wait_for_timeout(wait_ms)  # 等动态内容渲染
        html = page.content()
    except Exception as e:
        logger.error(f"[browser] fetch_url_rendered 失败 url={url}: {e}")
        return f"[渲染抓取失败] {type(e).__name__}: {e}"
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        if p is not None:
            p.stop()

    return _html_to_text(html, max_chars)


@tool(description="对网页截图保存为 PNG。需要 playwright + chromium（首次使用会提示安装）。截图保存到当前用户当天的 workspace/{user_id}/YYYYMMDD/screenshots/ 目录。")
def screenshot_url(url: str, full_page: bool = False, width: int = 1280, height: int = 720, timeout: int = 30) -> str:
    """对指定 URL 截图，返回保存路径。

    Args:
        url: 目标网页 URL（需含 http:// 或 https://）
        full_page: 是否截整页（包含滚动区域），默认 False 只截视口
        width: 浏览器视口宽度，默认 1280
        height: 浏览器视口高度，默认 720
        timeout: 页面加载超时秒数，默认 30
    """
    # 1. 检测 playwright + chromium
    err = _ensure_chromium()
    if err:
        return err

    # 2. 截图保存到当前用户的当天截图目录（workspace/{user_id}/YYYYMMDD/screenshots/，自动创建）
    save_dir = get_screenshot_dir(user_id_var.get())

    # 3. 生成文件名（URL 转安全文件名）
    safe_name = re.sub(r'[^\w\-.]', '_', url)[:60]
    filename = f"{safe_name}_{width}x{height}.png"
    save_path = save_dir / filename

    # 4. 调用 playwright 反检测浏览器截图
    p = browser = context = None
    try:
        p, browser, context = _launch_stealth_browser()
        page = context.new_page(viewport={"width": width, "height": height})
        logger.info(f"[browser] screenshot_url: {url} -> {save_path}")
        page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
        # 等一下让动态内容渲染
        page.wait_for_timeout(1500)
        page.screenshot(path=str(save_path), full_page=full_page)
    except Exception as e:
        logger.error(f"[browser] screenshot_url 失败 url={url}: {e}")
        return f"[截图失败] {type(e).__name__}: {e}"
    finally:
        if context is not None:
            context.close()
        if browser is not None:
            browser.close()
        if p is not None:
            p.stop()
    size_kb = save_path.stat().st_size // 1024
    logger.info(f"[browser] screenshot_url 成功: {save_path} ({size_kb} KB)")
    return f"[截图成功] 已保存到 {save_path}（{size_kb} KB，{width}x{height}）"


BROWSER_TOOLS = [fetch_url, extract_links, read_page_main_text, fetch_url_rendered, screenshot_url]
