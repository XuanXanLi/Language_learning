"""UserRepository 测试。

覆盖：建表、创建、查询、更新、删除、级联删除。
"""

import pytest
from pathlib import Path

from line_c.domain.user_profile import UserProfile
from line_c.engine.user_repository import UserRepository


@pytest.fixture
def repo():
    r = UserRepository(Path(":memory:"))
    yield r
    r.close()


@pytest.fixture
def sample_profile():
    return UserProfile(
        name="测试角色",
        english_level="middle",
        interests=["ai_tech", "finance"],
    )


class TestCreate:
    def test_create_returns_id(self, repo, sample_profile):
        new_id = repo.create(sample_profile)
        assert new_id > 0

    def test_create_persists(self, repo, sample_profile):
        new_id = repo.create(sample_profile)
        retrieved = repo.get_by_id(new_id)
        assert retrieved is not None
        assert retrieved.name == "测试角色"
        assert retrieved.english_level == "middle"
        assert "ai_tech" in retrieved.interests
        assert "finance" in retrieved.interests


class TestQuery:
    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id(999) is None

    def test_get_all_empty(self, repo):
        assert repo.get_all() == []

    def test_get_all_multiple(self, repo, sample_profile):
        repo.create(sample_profile)
        p2 = UserProfile(name="角色2", english_level="beginner", interests=["travel"])
        repo.create(p2)
        all_profiles = repo.get_all()
        assert len(all_profiles) == 2

    def test_count(self, repo, sample_profile):
        assert repo.count() == 0
        repo.create(sample_profile)
        assert repo.count() == 1


class TestUpdate:
    def test_update_name_and_level(self, repo, sample_profile):
        new_id = repo.create(sample_profile)
        profile = repo.get_by_id(new_id)
        profile.name = "改名后"
        profile.english_level = "high"
        assert repo.update(profile) is True

        updated = repo.get_by_id(new_id)
        assert updated.name == "改名后"
        assert updated.english_level == "high"

    def test_update_nonexistent(self, repo):
        ghost = UserProfile(id=999, name="不存在")
        assert repo.update(ghost) is False


class TestDelete:
    def test_delete_removes(self, repo, sample_profile):
        new_id = repo.create(sample_profile)
        assert repo.delete(new_id) is True
        assert repo.get_by_id(new_id) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete(999) is False
