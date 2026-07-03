"""文章正文提取器。

从原文 URL 抓取 HTML 页面，提取正文文本内容。
用于 RSS 预览时获取完整的文章内容，供 LLM 生成高质量中文摘要。

纯标准库实现，零额外依赖。
"""

import html as html_mod
import re
import urllib.request
from typing import Optional


# 常见的中文文章正文容器 class 名
_ARTICLE_CLASSES = [
    "article-content", "post-content", "article-body", "entry-content",
    "article-text", "post-body", "content-article", "article-detail",
    "article", "post", "entry", "detail-content", "news-content",
    "art-con", "article-con", "text-con",
]

# 要移除的非正文标签
_REMOVE_TAGS = [
    (r"<script[^>]*>.*?</script>", re.DOTALL),
    (r"<style[^>]*>.*?</style>", re.DOTALL),
    (r"<nav[^>]*>.*?</nav>", re.DOTALL),
    (r"<footer[^>]*>.*?</footer>", re.DOTALL),
    (r"<header[^>]*>.*?</header>", re.DOTALL),
    (r"<aside[^>]*>.*?</aside>", re.DOTALL),
    (r"<!--.*?-->", re.DOTALL),
]


def extract_article_text(html_text: str, max_chars: int = 3000) -> str:
    """从 HTML 中提取正文文本。

    策略：
    1. 先尝试定位 <article> / <main> 标签
    2. 查找常见文章内容的 class 名
    3. 移除 script/style/nav/footer/header 等非正文标签
    4. 剥离所有 HTML 标签，提取纯文本
    5. 截取前 max_chars 字符
    """
    if not html_text:
        return ""

    # Step 1: 尝试定位文章主体区域
    content_html = _find_article_area(html_text)

    # Step 2: 移除非正文标签
    for pattern, flags in _REMOVE_TAGS:
        content_html = re.sub(pattern, "", content_html, flags=flags)

    # Step 3: 剥离 HTML 标签
    text = re.sub(r"<[^>]+>", " ", content_html)
    # 解码 HTML 实体 (&amp; → &, &#xXXXX → 字符, 等)
    text = html_mod.unescape(text)
    # 合并空白
    text = re.sub(r"\s+", " ", text).strip()

    # Step 4: 截断
    if len(text) > max_chars:
        # 在最后一个完整句号/换行处截断
        cutoff = text.rfind("。", max_chars - 200, max_chars)
        if cutoff == -1:
            cutoff = text.rfind(".", max_chars - 200, max_chars)
        if cutoff == -1 or cutoff < max_chars // 2:
            cutoff = max_chars
        text = text[:cutoff + 1] if text[cutoff:cutoff + 1] in ("。", ".") else text[:cutoff]

    return text


def _find_article_area(html_text: str) -> str:
    """尝试定位文章正文所在的 HTML 区域。"""

    # 策略 A: <article> 标签
    m = re.search(r"<article[^>]*>(.*?)</article>", html_text, re.DOTALL)
    if m and len(m.group(1)) > 200:
        return m.group(1)

    # 策略 B: <main> 标签
    m = re.search(r"<main[^>]*>(.*?)</main>", html_text, re.DOTALL)
    if m and len(m.group(1)) > 200:
        return m.group(1)

    # 策略 C: 常见文章 class
    for cls in _ARTICLE_CLASSES:
        # <div class="...article-content...">
        pattern = rf'<[^>]+class\s*=\s*"[^"]*\b{re.escape(cls)}\b[^"]*"[^>]*>(.*?)</(?:div|section|article)>'
        m = re.search(pattern, html_text, re.DOTALL)
        if m and len(m.group(1)) > 200:
            return m.group(1)

    # 策略 D: 直接使用完整 HTML（最后兜底）
    return html_text


def fetch_and_extract(url: str, timeout: int = 8) -> Optional[str]:
    """抓取 URL 并提取正文文本。失败返回 None。"""
    if not url:
        return None

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 只处理 HTML 响应
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type and "text" not in content_type:
                return None

            raw = resp.read()
            # 尝试 UTF-8 解码
            for encoding in ("utf-8", "gbk", "gb2312", "gb18030", "latin-1"):
                try:
                    html_text = raw.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                html_text = raw.decode("utf-8", errors="replace")

        return extract_article_text(html_text)

    except Exception:
        return None
