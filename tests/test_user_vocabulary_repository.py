"""UserVocabularyRepository 测试。

覆盖：建表、点击取词(upsert)、复习队列查询、SM-2更新、掌握统计。
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from line_c.engine.user_vocabulary_repository import UserVocabularyRepository


@pytest.fixture
def repo():
    r = UserVocabularyRepository(Path(":memory:"))
    yield r
    r.close()


class TestUpsertLookup:
    def test_first_lookup_creates_record(self, repo):
        is_new = repo.upsert_lookup(word="algorithm", user_id=1, session_id=1)
        assert is_new is True

        record = repo.get_word("algorithm", user_id=1)
        assert record is not None
        assert record["word"] == "algorithm"
        assert record["state"] == "NEW"
        assert record["lookup_count"] == 1
        assert record["session_id"] == 1

    def test_second_lookup_increments_count(self, repo):
        repo.upsert_lookup(word="algorithm", user_id=1)
        is_new = repo.upsert_lookup(word="algorithm", user_id=1, session_id=2)
        assert is_new is False

        record = repo.get_word("algorithm", user_id=1)
        assert record["lookup_count"] == 2

    def test_same_word_different_users(self, repo):
        repo.upsert_lookup(word="algorithm", user_id=1)
        repo.upsert_lookup(word="algorithm", user_id=2)

        r1 = repo.get_word("algorithm", user_id=1)
        r2 = repo.get_word("algorithm", user_id=2)
        assert r1["lookup_count"] == 1
        assert r2["lookup_count"] == 1

    def test_next_review_set_to_created_at_for_new(self, repo):
        repo.upsert_lookup(word="test", user_id=1)
        record = repo.get_word("test", user_id=1)
        assert record["next_review_at"] is not None


class TestReviewQueue:
    def test_queue_returns_new_words(self, repo):
        repo.upsert_lookup(word="algorithm", user_id=1)
        repo.upsert_lookup(word="paradigm", user_id=1)

        queue = repo.get_review_queue(user_id=1, limit=20)
        assert len(queue) == 2
        words = [q["word"] for q in queue]
        assert "algorithm" in words
        assert "paradigm" in words

    def test_queue_respects_limit(self, repo):
        for i in range(25):
            repo.upsert_lookup(word=f"word_{i}", user_id=1)

        queue = repo.get_review_queue(user_id=1, limit=10)
        assert len(queue) == 10

    def test_queue_excludes_mastered(self, repo):
        repo.upsert_lookup(word="algorithm", user_id=1)
        # Simulate mastering
        repo.update_review(
            word="algorithm", user_id=1, state="MASTERED",
            repetition=5, interval_days=30.0, ef=2.5,
            consecutive_correct=5,
            next_review_at=(datetime.now() + timedelta(days=30)).isoformat(),
        )
        queue = repo.get_review_queue(user_id=1)
        assert len(queue) == 0

    def test_queue_only_due_words(self, repo):
        repo.upsert_lookup(word="algorithm", user_id=1)
        # Set next_review to future
        future = (datetime.now() + timedelta(days=7)).isoformat()
        repo._conn.execute(
            "UPDATE user_vocabulary SET next_review_at = ? WHERE user_id = ? AND word = ?",
            (future, 1, "algorithm"),
        )
        repo._conn.commit()

        queue = repo.get_review_queue(user_id=1)
        assert len(queue) == 0

    def test_queue_empty_for_new_user(self, repo):
        assert repo.get_review_queue(user_id=999) == []


class TestUpdateReview:
    def test_updates_all_sm2_fields(self, repo):
        repo.upsert_lookup(word="algorithm", user_id=1)
        tomorrow = (datetime.now() + timedelta(days=1)).isoformat()

        ok = repo.update_review(
            word="algorithm", user_id=1,
            state="LEARNING", repetition=1, interval_days=1.0,
            ef=2.5, consecutive_correct=1,
            next_review_at=tomorrow,
        )
        assert ok is True

        record = repo.get_word("algorithm", user_id=1)
        assert record["state"] == "LEARNING"
        assert record["repetition"] == 1
        assert record["interval_days"] == 1.0
        assert record["ef"] == 2.5
        assert record["consecutive_correct"] == 1
        assert record["last_reviewed_at"] is not None

    def test_update_nonexistent(self, repo):
        ok = repo.update_review(
            word="nope", user_id=999,
            state="LEARNING", repetition=0, interval_days=1.0,
            ef=2.5, consecutive_correct=1,
            next_review_at=datetime.now().isoformat(),
        )
        assert ok is False


class TestSpotCheck:
    def test_spot_check_returns_mastered_words(self, repo):
        repo.upsert_lookup(word="mastered_word", user_id=1)
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        repo._conn.execute(
            """UPDATE user_vocabulary
               SET state='MASTERED', last_reviewed_at=?
               WHERE user_id=1 AND word='mastered_word'""",
            (old_date,),
        )
        repo._conn.commit()

        spots = repo.get_spot_check_words(user_id=1, max_count=1)
        assert len(spots) == 1
        assert spots[0]["word"] == "mastered_word"

    def test_spot_check_skips_recently_reviewed(self, repo):
        repo.upsert_lookup(word="mastered_word", user_id=1)
        recent = (datetime.now() - timedelta(days=5)).isoformat()
        repo._conn.execute(
            """UPDATE user_vocabulary
               SET state='MASTERED', last_reviewed_at=?
               WHERE user_id=1 AND word='mastered_word'""",
            (recent,),
        )
        repo._conn.commit()

        spots = repo.get_spot_check_words(user_id=1, max_count=1)
        assert len(spots) == 0


class TestCounts:
    def test_mastered_count(self, repo):
        repo.upsert_lookup(word="a", user_id=1)
        repo.upsert_lookup(word="b", user_id=1)
        repo.update_review("a", 1, "MASTERED", 3, 21.0, 2.5, 3, datetime.now().isoformat())
        assert repo.get_mastered_count(1) == 1
        assert repo.get_total_count(1) == 2

    def test_empty_counts(self, repo):
        assert repo.get_mastered_count(1) == 0
        assert repo.get_total_count(1) == 0


class TestGetBySession:
    def test_get_by_session(self, repo):
        repo.upsert_lookup(word="a", user_id=1, session_id=10)
        repo.upsert_lookup(word="b", user_id=1, session_id=10)
        repo.upsert_lookup(word="c", user_id=1, session_id=11)

        s10 = repo.get_by_session(10)
        assert len(s10) == 2
        words = [r["word"] for r in s10]
        assert "a" in words and "b" in words
