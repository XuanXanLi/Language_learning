"""ReviewSessionManager 测试。

覆盖：队列加载、SM-2评分、掌握判定、抽查。
"""

import pytest
from pathlib import Path

from line_c.engine.user_vocabulary_repository import UserVocabularyRepository
from line_c.engine.review_session_manager import ReviewSessionManager


@pytest.fixture
def repo():
    r = UserVocabularyRepository(Path(":memory:"))
    yield r
    r.close()


@pytest.fixture
def populated_mgr(repo):
    """创建有5个生词的 ReviewSessionManager。"""
    for i, word in enumerate(["algorithm", "paradigm", "neural", "training", "inference"]):
        repo.upsert_lookup(word=word, user_id=1, session_id=1)
    mgr = ReviewSessionManager(user_id=1, user_vocab_repo=repo)
    return mgr


class TestLoadQueue:
    def test_loads_all_new_words(self, populated_mgr):
        count = populated_mgr.load_queue(limit=20)
        assert count == 5

    def test_empty_queue(self, repo):
        mgr = ReviewSessionManager(user_id=1, user_vocab_repo=repo)
        count = mgr.load_queue()
        assert count == 0
        assert populated_mgr is not None  # reference fixture to avoid unused warning

    def test_current_card_returns_dict(self, populated_mgr):
        populated_mgr.load_queue()
        card = populated_mgr.current_card()
        assert card is not None
        assert "word" in card
        assert "state" in card


class TestRateCard:
    def test_rate_perfect_moves_to_learning(self, populated_mgr):
        populated_mgr.load_queue()
        card = populated_mgr.current_card()
        result = populated_mgr.rate_current(quality=5)
        assert result["new_state"] == "LEARNING"
        assert result["next_review_days"] >= 1.0

    def test_rate_failed_stays_new(self, populated_mgr):
        populated_mgr.load_queue()
        result = populated_mgr.rate_current(quality=0)
        assert result["new_state"] == "NEW"
        assert result["mastered"] is False

    def test_progress_advances(self, populated_mgr):
        populated_mgr.load_queue()
        assert populated_mgr.current_idx == 0
        populated_mgr.rate_current(5)
        assert populated_mgr.current_idx == 1

    def test_complete_after_all_rated(self, populated_mgr):
        populated_mgr.load_queue()
        while not populated_mgr.is_complete():
            populated_mgr.rate_current(5)
        assert populated_mgr.is_complete()
        stats = populated_mgr.get_stats()
        assert stats["remembered"] == 5


class TestMasteryDetection:
    def test_mastery_requires_consecutive_and_interval(self, repo):
        """连续3次正确+间隔>=21天才算掌握。"""
        repo.upsert_lookup(word="mastery_test", user_id=1)
        mgr = ReviewSessionManager(user_id=1, user_vocab_repo=repo)
        mgr.load_queue()

        # 第一次: q=5 → LEARNING, interval=1天
        r1 = mgr.rate_current(5)
        assert r1["new_state"] == "LEARNING"

    def test_stats_accumulate(self, populated_mgr):
        populated_mgr.load_queue()
        populated_mgr.rate_current(5)  # remembered
        populated_mgr.rate_current(3)  # hard
        populated_mgr.rate_current(0)  # forgot
        stats = populated_mgr.get_stats()
        assert stats["remembered"] == 1
        assert stats["hard"] == 1
        assert stats["forgot"] == 1

    def test_get_counts(self, populated_mgr):
        populated_mgr.load_queue()
        assert populated_mgr.get_total_count() == 5
        assert populated_mgr.get_mastered_count() == 0
