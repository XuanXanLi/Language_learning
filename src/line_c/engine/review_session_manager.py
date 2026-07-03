"""复习会话管理器。

管理单次复习会话：加载队列、SM-2评分、掌握判定、抽查。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..engine.sm2_srs import sm2_calculate


class ReviewSessionManager:
    """管理一次复习会话（闪卡模式）。"""

    MASTERY_CONSECUTIVE = 3        # 连续正确次数达标
    MASTERY_MIN_INTERVAL = 21.0    # 最小间隔天数
    SPOT_CHECK_INTERVAL = 30       # 抽查间隔天数

    def __init__(self, user_id: int, user_vocab_repo):
        self.user_id = user_id
        self.vocab_repo = user_vocab_repo
        self.cards: List[Dict] = []
        self.current_idx: int = 0
        self.stats = {"remembered": 0, "hard": 0, "forgot": 0}

    def load_queue(self, limit: int = 20) -> int:
        """加载复习队列。返回卡片数。"""
        # 加到期词
        due = self.vocab_repo.get_review_queue(self.user_id, limit=limit)

        # 加抽查词（已掌握但满30天的）
        spot = self.vocab_repo.get_spot_check_words(self.user_id, max_count=2)

        # 合并，前端优先
        self.cards = due + spot
        self.current_idx = 0
        self.stats = {"remembered": 0, "hard": 0, "forgot": 0}
        return len(self.cards)

    def current_card(self) -> Optional[Dict]:
        """获取当前卡片数据。"""
        if not self.cards or self.current_idx >= len(self.cards):
            return None
        return self.cards[self.current_idx]

    def rate_current(self, quality: int) -> Dict:
        """对当前卡片评分并持久化。

        quality: 0=没想起来, 3=有点模糊, 5=想起来了
        返回: {state, mastered, next_review_days, is_last}
        """
        card = self.cards[self.current_idx]

        # SM-2 计算
        result = sm2_calculate(
            quality=quality,
            repetition=card.get("repetition", 0),
            interval=card.get("interval_days", 0.0),
            ef=card.get("ef", 2.5),
        )

        # 连续正确
        if quality >= 3:
            consecutive = card.get("consecutive_correct", 0) + 1
        else:
            consecutive = 0

        # 掌握判定
        new_state = card.get("state", "NEW")
        if new_state == "NEW" and quality >= 3:
            new_state = "LEARNING"
        if (consecutive >= self.MASTERY_CONSECUTIVE
                and result.interval_days >= self.MASTERY_MIN_INTERVAL):
            new_state = "MASTERED"

        # 已掌握词抽查：保留 MASTERED，更新间隔
        if card.get("state") == "MASTERED":
            new_state = "MASTERED"

        # 写入 DB
        next_review = datetime.now() + timedelta(days=result.interval_days)
        self.vocab_repo.update_review(
            word=card["word"],
            user_id=self.user_id,
            state=new_state,
            repetition=result.repetition,
            interval_days=result.interval_days,
            ef=result.ef,
            consecutive_correct=consecutive,
            next_review_at=next_review.isoformat(),
        )

        # 统计
        if quality == 5:
            self.stats["remembered"] += 1
        elif quality == 3:
            self.stats["hard"] += 1
        else:
            self.stats["forgot"] += 1

        self.current_idx += 1
        is_last = self.current_idx >= len(self.cards)

        return {
            "new_state": new_state,
            "mastered": new_state == "MASTERED",
            "next_review_days": result.interval_days,
            "is_last": is_last,
        }

    def has_next(self) -> bool:
        return self.current_idx < len(self.cards)

    def progress(self) -> tuple:
        """返回 (current, total)。"""
        return (self.current_idx + 1, len(self.cards))

    def is_complete(self) -> bool:
        return self.current_idx >= len(self.cards)

    def get_stats(self) -> Dict:
        return dict(self.stats)

    def get_mastered_count(self) -> int:
        return self.vocab_repo.get_mastered_count(self.user_id)

    def get_total_count(self) -> int:
        return self.vocab_repo.get_total_count(self.user_id)
