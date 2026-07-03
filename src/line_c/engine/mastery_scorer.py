"""掌握度评分器。

Mastery score（掌握度分数）是 0-100 的长期学习进度。
状态机负责大阶段，掌握度负责更细的变化。
"""

from ..domain.learning_event import LearningEventType


class MasteryScorer:
    """根据学习事件计算掌握度变化。"""

    MIN_SCORE = 0
    MAX_SCORE = 100

    BASE_DELTAS = {
        LearningEventType.INTRODUCED: 5,
        LearningEventType.ATTEMPTED: 10,
        LearningEventType.CORRECT_USAGE: 15,
        LearningEventType.WRONG_USAGE: -10,
        LearningEventType.CORRECTED: 0,
        LearningEventType.REVIEW_PASSED: 15,
        LearningEventType.REVIEW_FAILED: -15,
        LearningEventType.MASTERED: 0,
    }

    def delta_for(self, event_type: LearningEventType, quality: int | None = None) -> int:
        """返回某个事件带来的掌握度变化。"""
        if event_type == LearningEventType.CORRECT_USAGE and quality is not None:
            if quality >= 5:
                return 20
            if quality == 4:
                return 15
            if quality == 3:
                return 5
            return -10

        if event_type == LearningEventType.WRONG_USAGE and quality is not None:
            return -15 if quality <= 1 else -10

        if event_type == LearningEventType.MASTERED:
            return 0

        return self.BASE_DELTAS[event_type]

    def apply_delta(self, current_score: int, delta: int) -> int:
        """把 delta 应用到当前分数，并限制在 0-100。"""
        return max(self.MIN_SCORE, min(self.MAX_SCORE, current_score + delta))

    def score_event(
        self,
        current_score: int,
        event_type: LearningEventType,
        quality: int | None = None,
    ) -> tuple[int, int]:
        """根据事件返回 (新分数, 分数变化)。"""
        delta = self.delta_for(event_type, quality)
        new_score = self.apply_delta(current_score, delta)

        if event_type == LearningEventType.MASTERED and new_score < 85:
            delta += 85 - new_score
            new_score = 85

        return new_score, delta
