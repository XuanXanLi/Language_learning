"""ChatSessionRepository 测试。

覆盖：建表、创建、查询、结束会话。
"""

import pytest
from pathlib import Path

from line_c.domain.chat_session import ChatSession
from line_c.engine.chat_session_repository import ChatSessionRepository


@pytest.fixture
def repo():
    r = ChatSessionRepository(Path(":memory:"))
    yield r
    r.close()


@pytest.fixture
def sample_session():
    return ChatSession(
        user_id=1,
        topic_title="AI 训练成本下降",
        topic_source="llm",
    )


class TestCreate:
    def test_create_returns_id(self, repo, sample_session):
        new_id = repo.create(sample_session)
        assert new_id > 0

    def test_create_persists(self, repo, sample_session):
        new_id = repo.create(sample_session)
        retrieved = repo.get_by_id(new_id)
        assert retrieved is not None
        assert retrieved.user_id == 1
        assert retrieved.topic_title == "AI 训练成本下降"
        assert retrieved.topic_source == "llm"
        assert retrieved.started_at != ""


class TestQuery:
    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id(999) is None

    def test_get_by_user(self, repo, sample_session):
        repo.create(sample_session)
        s2 = ChatSession(user_id=1, topic_title="另一个话题", topic_source="user")
        repo.create(s2)
        # 角色 2 的会话不会出现
        s3 = ChatSession(user_id=2, topic_title="别人的话题", topic_source="llm")
        repo.create(s3)

        user1_sessions = repo.get_by_user(1)
        assert len(user1_sessions) == 2
        assert all(s.user_id == 1 for s in user1_sessions)

    def test_get_by_user_empty(self, repo):
        assert repo.get_by_user(999) == []


class TestEndSession:
    def test_end_session_sets_timestamp(self, repo, sample_session):
        new_id = repo.create(sample_session)
        before = repo.get_by_id(new_id)
        assert before.ended_at is None

        assert repo.end_session(new_id) is True
        after = repo.get_by_id(new_id)
        assert after.ended_at is not None

    def test_end_session_nonexistent(self, repo):
        assert repo.end_session(999) is False
