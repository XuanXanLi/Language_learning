"""SRS 复习调度器（SRS Scheduler）。

在 SM-2 算法之上管理多个词汇的复习队列：
- 哪些词需要复习？
- 什么时候复习？
- 复习后的调度结果如何？

用法：
    scheduler = SRSScheduler()
    scheduler.schedule(word="abandon", quality=4)  # 记录一次复习
    due_words = scheduler.get_due_words()           # 列出到期的词
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .sm2_srs import sm2_calculate, SM2Result


@dataclass
class ScheduledWord:
    """一个词的复习调度信息。

    存储了 SM-2 计算所需的所有状态变量。
    """
    word: str
    repetition: int = 0
    interval: float = 0.0
    ef: float = 2.5
    next_review_at: Optional[datetime] = None
    review_history: List[dict] = field(default_factory=list)


class SRSScheduler:
    """管理多个词的间隔复习调度。

    内部维护一个字典 {词: ScheduledWord}，
    提供调度、查询和到期检测功能。
    """

    def __init__(self):
        self._words: Dict[str, ScheduledWord] = {}

    def schedule(self, word: str, quality: int) -> SM2Result:
        """记录一次复习并计算下次复习时间。

        如果是新词（首次调度），自动初始化为 SCHEDULED 状态。
        如果是已有词，用当前参数 + 本次 quality 做 SM-2 计算。

        返回：
        - SM2Result: 计算结果（可用于日志/UI 显示）
        """
        if quality < 0 or quality > 5:
            raise ValueError(f"Quality must be 0-5, got {quality}")

        existing = self._words.get(word)
        if existing:
            rep = existing.repetition
            interval = existing.interval
            ef = existing.ef
        else:
            rep = 0
            interval = 0.0
            ef = 2.5

        result = sm2_calculate(
            quality=quality,
            repetition=rep,
            interval=interval,
            ef=ef,
        )

        now = datetime.now()
        next_review = now + timedelta(days=result.interval_days)

        self._words[word] = ScheduledWord(
            word=word,
            repetition=result.repetition,
            interval=result.interval_days,
            ef=result.ef,
            next_review_at=next_review,
            review_history=existing.review_history + [{
                "quality": quality,
                "timestamp": now.isoformat(),
                "result": result,
            }] if existing else [{
                "quality": quality,
                "timestamp": now.isoformat(),
                "result": result,
            }],
        )

        return result

    def get_due_words(self, now: Optional[datetime] = None) -> List[str]:
        """返回所有到期需要复习的词列表。

        now: 当前时间，默认 datetime.now()（可注入用于测试）
        """
        now = now or datetime.now()
        due = []
        for word, sw in self._words.items():
            if sw.next_review_at is not None and sw.next_review_at <= now:
                due.append(word)
        return due

    def get_scheduled_word(self, word: str) -> Optional[ScheduledWord]:
        """获取某个词的调度信息。"""
        return self._words.get(word)

    def all_words(self) -> Dict[str, ScheduledWord]:
        """返回所有已调度的词。"""
        return dict(self._words)

    def word_count(self) -> int:
        """已调度的词数。"""
        return len(self._words)

    def upcoming_reviews(self, within_days: int = 3) -> List[ScheduledWord]:
        """返回未来 N 天内需要复习的词（含到期和即将到期的）。"""
        now = datetime.now()
        cutoff = now + timedelta(days=within_days)
        upcoming = []
        for sw in self._words.values():
            if sw.next_review_at is not None and sw.next_review_at <= cutoff:
                upcoming.append(sw)
        upcoming.sort(key=lambda x: x.next_review_at or datetime.max)
        return upcoming
