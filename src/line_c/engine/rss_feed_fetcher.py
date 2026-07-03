"""RSS 新闻抓取器。

从中文 RSS 源抓取热点新闻标题和摘要，转为 TopicCard。
支持持久化每日缓存、AI 内容筛选、并发抓取、自动降级。
"""

import concurrent.futures
import re
import time
from datetime import date
from typing import Dict, List, Optional

import feedparser

from .rss_cache_manager import RssCacheManager
from .topic_generator import TopicCard
from ..config import RSS_CACHE_FILE

# ── 中文 RSS 源定义（按兴趣领域）──
# 每个领域 2-3 个源，优先使用有原生 RSS 的站点
RSS_SOURCES: Dict[str, List[dict]] = {
    "ai_tech": [
        {
            "name": "36氪",
            "url": "https://36kr.com/feed",
            "lang": "zh",
        },
        {
            "name": "少数派",
            "url": "https://sspai.com/feed",
            "lang": "zh",
        },
        {
            "name": "IT之家",
            "url": "https://www.ithome.com/rss/",
            "lang": "zh",
        },
    ],
    "finance": [
        {
            "name": "虎嗅",
            "url": "https://www.huxiu.com/rss/0.xml",
            "lang": "zh",
        },
        {
            "name": "雪球热帖",
            "url": "https://xueqiu.com/hots/topic/rss",
            "lang": "zh",
        },
    ],
    "science": [
        {
            "name": "果壳网",
            "url": "https://www.guokr.com/rss/",
            "lang": "zh",
        },
        {
            "name": "环球科学",
            "url": "https://www.huanqiukexue.com/rss",
            "lang": "zh",
        },
    ],
    "history": [
        {
            "name": "全历史",
            "url": "https://www.allhistory.com/rss",
            "lang": "zh",
        },
        {
            "name": "国家人文历史",
            "url": "https://www.sohu.com/media/273106",
            "lang": "zh",
        },
    ],
    "travel": [
        {
            "name": "穷游网",
            "url": "https://www.qyer.com/feed",
            "lang": "zh",
        },
        {
            "name": "马蜂窝",
            "url": "https://www.mafengwo.cn/feed",
            "lang": "zh",
        },
    ],
    "music": [
        {
            "name": "好奇心日报",
            "url": "http://www.qdaily.com/feed.xml",
            "lang": "zh",
        },
        {
            "name": "机核",
            "url": "https://www.gcores.com/rss",
            "lang": "zh",
        },
    ],
    "sports": [
        {
            "name": "虎扑",
            "url": "https://www.hupu.com/rss",
            "lang": "zh",
        },
        {
            "name": "新浪体育",
            "url": "https://sports.sina.com.cn/rss",
            "lang": "zh",
        },
    ],
    "games": [
        {
            "name": "游民星空",
            "url": "https://www.gamersky.com/feed",
            "lang": "zh",
        },
        {
            "name": "触乐",
            "url": "http://www.chuapp.com/feed",
            "lang": "zh",
        },
    ],
}


class RSSFeedFetcher:
    """RSS 新闻抓取器 — 中文源 + 每日持久化缓存 + AI 筛选。

    用法:
        fetcher = RSSFeedFetcher()
        topics = fetcher.fetch(["ai_tech", "finance"], count=6)
        # → List[TopicCard]，同一天内从缓存读取，跨天自动重新抓取

        # AI 筛选（仅 cloud 模式）
        filtered = fetcher.filter_with_llm(topics, llm)
    """

    def __init__(self):
        self._cache_mgr = RssCacheManager(RSS_CACHE_FILE)

    # ── 主抓取入口 ────────────────────────────────────────

    def fetch(
        self, interests: List[str], count: int = 6, timeout: int = 10
    ) -> List[TopicCard]:
        """按兴趣领域获取话题。

        同一天内从磁盘缓存读取（不访问网络）；跨天则重新抓取并更新缓存。
        """
        cache = self._cache_mgr.load_cache()

        # ── 缓存命中（同一天）──
        if self._cache_mgr.is_fresh_for_today(cache):
            cached = self._cache_mgr.get_all_cached_topics(cache, interests)
            if cached:
                return self._dicts_to_cards(cached)[:count]

        # ── 缓存未命中 → 抓取 ──
        return self._fetch_and_cache(interests, count, timeout)

    def _fetch_and_cache(
        self, interests: List[str], count: int, timeout: int
    ) -> List[TopicCard]:
        """抓取所有源，存入磁盘缓存，返回匹配的话题。"""
        cache = self._cache_mgr.load_cache()

        # 按类别并发抓取
        all_cards_by_category: Dict[str, List[TopicCard]] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures: dict = {}
            for interest in interests:
                sources = RSS_SOURCES.get(interest, [])
                for src in sources:
                    future = executor.submit(
                        self._fetch_one, src["url"], src["name"], interest, timeout
                    )
                    futures[future] = (interest, src["name"])

            for future in concurrent.futures.as_completed(futures, timeout=timeout + 5):
                interest, source_name = futures[future]
                try:
                    cards = future.result()
                    if cards:
                        all_cards_by_category.setdefault(interest, []).extend(cards)
                except Exception:
                    pass  # 单个源失败不影响其他

        # 存入缓存（按类别）
        for interest in interests:
            if interest in all_cards_by_category:
                topic_dicts = self._cards_to_dicts(all_cards_by_category[interest])
                self._cache_mgr.store_topics(cache, interest, topic_dicts)

        # 也缓存空结果（避免反复重试当天已失败的源）
        for interest in interests:
            if interest not in all_cards_by_category:
                # 保留旧缓存（如果有），没有就存空列表
                old = self._cache_mgr.get_cached_topics(cache, interest)
                if not old:
                    self._cache_mgr.store_topics(cache, interest, [])

        self._cache_mgr.save_cache(cache)

        # 去重 + 截取
        seen_titles: set = set()
        unique: List[TopicCard] = []
        for interest in interests:
            for card in all_cards_by_category.get(interest, []):
                if card.title not in seen_titles:
                    seen_titles.add(card.title)
                    unique.append(card)

        return unique[:count]

    # ── 单源抓取 ──────────────────────────────────────────

    def _fetch_one(
        self, url: str, source_name: str, interest: str, timeout: int
    ) -> List[TopicCard]:
        """抓取单个 RSS 源，解析为 TopicCard 列表。"""
        try:
            resp = feedparser.parse(
                url,
                agent="VocaLand/2.0",
                response_headers={"timeout": str(timeout)},
            )
        except Exception:
            return []

        if resp.bozo and not resp.entries:
            return []

        cards = []
        for entry in resp.entries[:5]:  # 每个源取前 5 条
            title = str(entry.get("title", "")).strip()
            summary = str(entry.get("summary", "") or entry.get("description", "")).strip()
            link = str(entry.get("link", ""))

            # 去掉 HTML 标签
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            # 截断摘要
            if len(summary) > 150:
                summary = summary[:147] + "..."

            if title:
                cards.append(TopicCard(
                    title=title,
                    summary=summary,
                    source=f"📰 {source_name}",
                    source_url=link,
                ))

        return cards

    # ── AI 内容筛选 ───────────────────────────────────────

    def filter_with_llm(self, topics: List[TopicCard], llm) -> List[TopicCard]:
        """用 LLM 筛选话题 — 判断哪些值得推送给用户。

        仅在 cloud 模式（LLM 可用）时调用。
        筛选维度：讨论价值、广泛吸引力、教育意义、安全性、趣味性。
        """
        if not topics or not llm:
            return topics

        if len(topics) <= 6:
            # 话题少时不筛选，全保留
            return topics

        # 构建审查清单
        items_text = ""
        for i, t in enumerate(topics):
            items_text += f"[{i}] 标题: {t.title} | 来源: {t.source}\n"

        prompt = f"""你是 VocaLand（一款面向中国人的英语学习 App）的内容策展人。
用户通过英语对话练习来学英语，你需要从今日热点中选出最适合推荐的话题。

审查标准：
1. **讨论价值**：这个话题是否适合用英语展开对话？
2. **广泛吸引力**：是否大多数人都会感兴趣，而非过于小众？
3. **教育价值**：是否能增长见识或开阔眼界？
4. **安全性**：不含政治敏感、暴力、成人、犯罪细节内容
5. **趣味性**：是否能让人想开口聊聊？

今日热点候选：
{items_text}

请从以上候选中挑选最多 12 个最值得推送的话题。
返回纯 JSON：{{"approved": [0, 3, 5, ...], "reason": "一句话说明筛选理由"}}
不要返回 JSON 以外的任何文字。"""

        try:
            resp = llm.chat(
                system_prompt="你是一个内容策展助手，输出纯 JSON，不做其他解释。",
                messages=[{"role": "user", "content": prompt}],
            )
            if not resp or not resp.text:
                return topics  # LLM 调用失败，全保留

            import json
            text = resp.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]

            result = json.loads(text)
            approved_indices = result.get("approved", [])

            if not approved_indices:
                return topics[:8]  # LLM 一个都不批 → 取前 8 个

            # 标记批准状态
            reason = result.get("reason", "")
            approved_set = set(approved_indices)
            for i, t in enumerate(topics):
                t.approved = i in approved_set
                t.approval_reason = reason if t.approved else ""

            return [t for t in topics if t.approved]

        except Exception:
            return topics  # 解析失败，全保留

    # ── Mock 模式规则筛选 ─────────────────────────────────

    @staticmethod
    def basic_relevance_filter(topics: List[TopicCard]) -> List[TopicCard]:
        """无 LLM 时的基础规则筛选。

        过滤明显的噪音/广告/低质量标题。
        """
        filtered = []
        for t in topics:
            title = t.title.strip()
            summary = t.summary.strip()

            # 标题长度 5-50 字符
            if len(title) < 4 or len(title) > 50:
                continue
            # 摘要至少 10 字符
            if len(summary) < 10:
                continue
            # 排除全大写（通常是广告）
            if title.isupper() and len(title) > 6:
                continue
            # 排除纯符号标题
            if not any(c.isalnum() or '一' <= c <= '鿿' for c in title):
                continue

            filtered.append(t)

        return filtered

    # ── 缓存管理 ──────────────────────────────────────────

    def clear_cache(self):
        """清除磁盘缓存（手动刷新或测试用）。"""
        self._cache_mgr.clear()

    # ── 序列化辅助 ─────────────────────────────────────────

    @staticmethod
    def _cards_to_dicts(cards: List[TopicCard]) -> List[dict]:
        return [
            {
                "title": c.title,
                "summary": c.summary,
                "source": c.source,
                "source_url": c.source_url,
                "approved": c.approved,
                "approval_reason": c.approval_reason,
            }
            for c in cards
        ]

    @staticmethod
    def _dicts_to_cards(dicts: List[dict]) -> List[TopicCard]:
        return [
            TopicCard(
                title=d.get("title", ""),
                summary=d.get("summary", ""),
                source=d.get("source", ""),
                source_url=d.get("source_url", ""),
                approved=d.get("approved", True),
                approval_reason=d.get("approval_reason", ""),
            )
            for d in dicts
        ]
