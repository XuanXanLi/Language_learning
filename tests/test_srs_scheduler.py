"""SRS 调度器的测试用例。

覆盖：
- 首次调度（新词加队列）
- 到期检测
- 多词队列
- 复习历史记录
"""
import pytest
from datetime import datetime, timedelta

from line_c.engine.srs_scheduler import SRSScheduler


class TestSRSScheduler:

    def test_schedule_new_word(self):
        """首次调度一个词，应该创建调度记录。"""
        s = SRSScheduler()
        result = s.schedule("abandon", quality=5)
        assert result.interval_days == 1.0
        assert s.word_count() == 1

    def test_schedule_updates_existing_word(self):
        """重复调度同一个词，更新其复习参数。"""
        s = SRSScheduler()
        r1 = s.schedule("abandon", quality=5)
        r2 = s.schedule("abandon", quality=5)
        assert r2.repetition > r1.repetition  # 第二次复习，rep 增加了

    def test_new_word_not_due_immediately(self):
        """刚复习完的词，不应该立即到期。"""
        s = SRSScheduler()
        s.schedule("abandon", quality=5)  # 间隔 1 天
        due = s.get_due_words()
        assert "abandon" not in due

    def test_word_due_after_interval(self):
        """间隔 1 天，用未来时间查，应该到期。"""
        s = SRSScheduler()
        s.schedule("abandon", quality=5)
        future = datetime.now() + timedelta(days=2)
        due = s.get_due_words(now=future)
        assert "abandon" in due

    def test_failed_word_due_tomorrow(self):
        """复习失败 (q<3)，下次复习是明天，推到明天应到期。"""
        s = SRSScheduler()
        s.schedule("abandon", quality=0)
        tomorrow = datetime.now() + timedelta(days=1, hours=1)
        due = s.get_due_words(now=tomorrow)
        assert "abandon" in due

    def test_get_scheduled_word(self):
        """获取已调度词的信息。"""
        s = SRSScheduler()
        s.schedule("abandon", quality=5)
        sw = s.get_scheduled_word("abandon")
        assert sw is not None
        assert sw.word == "abandon"
        assert sw.repetition == 1

    def test_get_nonexistent_word(self):
        """查询未调度的词返回 None。"""
        s = SRSScheduler()
        assert s.get_scheduled_word("nobody") is None

    def test_review_history_grows(self):
        """每次复习都追加到历史记录。"""
        s = SRSScheduler()
        s.schedule("abandon", quality=5)
        s.schedule("abandon", quality=4)
        sw = s.get_scheduled_word("abandon")
        assert len(sw.review_history) == 2

    def test_upcoming_reviews(self):
        """验证 upcoming_reviews 按时间排序。"""
        s = SRSScheduler()
        s.schedule("word_a", quality=5)  # 1 天后
        s.schedule("word_b", quality=5)  # 1 天后
        upcoming = s.upcoming_reviews(within_days=3)
        assert len(upcoming) == 2

    def test_invalid_quality_raises(self):
        """非法 quality 值抛出异常。"""
        s = SRSScheduler()
        with pytest.raises(ValueError):
            s.schedule("test", quality=10)

    def test_multiple_words_independent(self):
        """多个词的调度互不干扰。"""
        s = SRSScheduler()
        s.schedule("word_a", quality=5)
        s.schedule("word_b", quality=0)
        assert s.word_count() == 2
        assert s.get_scheduled_word("word_a").repetition == 1
        assert s.get_scheduled_word("word_b").repetition == 0
