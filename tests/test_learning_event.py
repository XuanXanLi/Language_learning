"""学习事件数据结构测试。"""

from line_c.domain.learning_event import EvaluationResult, LearningEvent, LearningEventType


class TestEvaluationResult:

    def test_quality_is_clamped(self):
        result = EvaluationResult(
            word="persist",
            attempted=True,
            correct=True,
            quality=9,
        )
        assert result.quality == 5

    def test_not_attempted_cannot_be_correct(self):
        result = EvaluationResult(
            word="persist",
            attempted=False,
            correct=True,
            quality=0,
        )
        assert result.correct is False


class TestLearningEvent:

    def test_quality_is_clamped_when_present(self):
        event = LearningEvent(
            word="persist",
            event_type=LearningEventType.CORRECT_USAGE,
            quality=-1,
        )
        assert event.quality == 0

    def test_event_type_values_are_stable(self):
        assert LearningEventType.INTRODUCED.value == "introduced"
        assert LearningEventType.WRONG_USAGE.value == "wrong_usage"
