"""RSS 持久化缓存管理器。

管理每日 RSS 抓取结果的 JSON 文件缓存。
- 同一天内只抓一次，后续从缓存读取
- 跨天自动触发重新抓取
- 原子写入（先写临时文件再 rename），防崩溃丢数据
"""

import json
import os
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional


CACHE_VERSION = 1


class RssCacheManager:
    """RSS 每日缓存管理器。

    用法:
        mgr = RssCacheManager(cache_path)
        cache = mgr.load_cache()
        if mgr.is_fresh_for_today(cache):
            topics = mgr.get_cached_topics(cache, "ai_tech")
        else:
            # 抓取新数据...
            cache = mgr.store_topics(cache, "ai_tech", new_topics)
            mgr.save_cache(cache)
    """

    def __init__(self, cache_path: Path):
        self._cache_path = cache_path

    # ── 核心读写 ──────────────────────────────────────────

    def load_cache(self) -> dict:
        """从磁盘加载缓存。文件缺失或损坏返回空字典。"""
        if not self._cache_path.exists():
            return self._empty_cache()

        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            # 版本兼容：如果版本不匹配，视为过期
            if data.get("version") != CACHE_VERSION:
                return self._empty_cache()
            return data
        except (json.JSONDecodeError, OSError):
            return self._empty_cache()

    def save_cache(self, cache: dict) -> None:
        """原子写入缓存到磁盘。

        先写临时文件，再 os.replace（Linux 上原子操作），
        保证写入过程中崩溃不会损坏已有数据。
        """
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)

        # 写临时文件
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix="rss_cache_",
            dir=str(self._cache_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            # 原子替换
            os.replace(tmp_path, str(self._cache_path))
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # ── 日期检查 ──────────────────────────────────────────

    @staticmethod
    def today_str() -> str:
        """返回今天的日期字符串 YYYY-MM-DD。"""
        return date.today().isoformat()

    def is_fresh_for_today(self, cache: dict) -> bool:
        """检查缓存是否是今天抓的。"""
        return cache.get("fetch_date") == self.today_str()

    # ── 话题存取 ──────────────────────────────────────────

    def get_cached_topics(self, cache: dict, category: str) -> List[dict]:
        """从缓存中取某个类别的所有话题。"""
        categories = cache.get("categories", {})
        return categories.get(category, [])

    def get_all_cached_topics(self, cache: dict, interests: List[str]) -> List[dict]:
        """从缓存中取所有匹配兴趣的话题（已去重）。"""
        seen_titles = set()
        result = []
        categories = cache.get("categories", {})
        for interest in interests:
            for topic in categories.get(interest, []):
                title = topic.get("title", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    result.append(topic)
        return result

    def store_topics(self, cache: dict, category: str, topics: List[dict]) -> dict:
        """将话题存入缓存。返回更新后的缓存字典。"""
        cache.setdefault("categories", {})
        cache["categories"][category] = topics
        cache["fetch_date"] = self.today_str()
        cache["version"] = CACHE_VERSION
        return cache

    # ── 辅助方法 ──────────────────────────────────────────

    def clear(self) -> None:
        """删除缓存文件（手动刷新或测试用）。"""
        if self._cache_path.exists():
            self._cache_path.unlink()

    @staticmethod
    def _empty_cache() -> dict:
        return {
            "version": CACHE_VERSION,
            "fetch_date": "",
            "categories": {},
        }
