"""MasteryScorer 测试。"""

from line_c.domain.learning_event import LearningEventType
from line_c.engine.mastery_scorer import MasteryScorer


class TestMasteryScorer:

    def test_introduced_adds_small_score(self):
        scorer = MasteryScorer()
        new_score, delta = scorer.score_event(0, LearningEventType.INTRODUCED)
        assert delta == 5
        assert new_score == 5

    def test_correct_usage_quality_5_adds_more_than_quality_4(self):
        scorer = MasteryScorer()
        score_4, delta_4 = scorer.score_event(10, LearningEventType.CORRECT_USAGE, quality=4)
        score_5, delta_5 = scorer.score_event(10, LearningEventType.CORRECT_USAGE, quality=5)
        assert delta_5 > delta_4
        assert score_5 > score_4

    def test_wrong_usage_does_not_go_below_zero(self):
        scorer = MasteryScorer()
        new_score, delta = scorer.score_event(3, LearningEventType.WRONG_USAGE, quality=1)
        assert delta == -15
        assert new_score == 0

    def test_score_is_capped_at_100(self):
        scorer = MasteryScorer()
        new_score, _ = scorer.score_event(95, LearningEventType.CORRECT_USAGE, quality=5)
        assert new_score == 100

    def test_mastered_sets_minimum_85(self):
        scorer = MasteryScorer()
        new_score, delta = scorer.score_event(40, LearningEventType.MASTERED)
        assert new_score == 85
        assert delta == 45
