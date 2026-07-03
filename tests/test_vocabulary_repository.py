"""VocabularyRepository 的测试用例。

测试策略：
- 每个测试独立运行，不依赖其他测试
- 使用 :memory: 数据库（SQLite 支持的内存模式），测试完自动销毁
- 覆盖：建表、插入、查询（按拼写/等级/话题/状态）、更新状态、关闭
"""
import pytest
from pathlib import Path

from line_c.domain.word import Word
from line_c.domain.vocabulary_state import VocabularyState
from line_c.engine.vocabulary_repository import VocabularyRepository


# ── 测试辅助：创建样本数据 ──

def make_word(word="test", level="cet4", tags=None) -> Word:
    """快速创建一个测试用的 Word 对象。"""
    return Word(
        word=word,
        phonetic="/test/",
        part_of_speech="n.",
        definition_en="a test word",
        definition_cn="测试词",
        examples=["This is a test."],
        level=level,
        topic_tags=tags or ["daily"],
        difficulty=0.3,
        synonyms=["exam"],
        antonyms=[],
    )


# ── 测试夹具（Fixture） ──
# pytest 的 fixture 机制：定义一个可复用的"准备步骤"，
# 每个测试函数可以通过参数名引用它。

@pytest.fixture
def repo():
    """创建一个使用内存数据库的 Repository。

    :memory: 是 SQLite 的特殊路径——数据库只在内存中存在，
    连接关闭后数据消失。测试用它不需要清理文件。
    """
    r = VocabularyRepository(Path(":memory:"))
    yield r  # yield = 测试函数在这里执行
    r.close()


@pytest.fixture
def populated_repo(repo):
    """包含 3 个测试词的 Repository。"""
    words = [
        make_word("apple", "cet4", ["food"]),
        make_word("abandon", "cet4", ["emotion"]),
        make_word("budget", "cet6", ["work"]),
    ]
    repo.add_words(words)
    return repo


# ── 测试用例 ──

class TestVocabularyRepository:
    """Repository 的测试集合。

    类名以 Test 开头是 pytest 的约定——它会自动发现并执行里面的测试方法。
    """

    def test_create_tables(self, repo):
        """验证建表成功：新创建的仓库应该包含 words 表。"""
        row = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='words'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "words"

    def test_add_and_get_word(self, repo):
        """添加一个词，然后查回来，字段应该一致。"""
        w = make_word("hello")
        repo.add_word(w)
        got = repo.get_word("hello")
        assert got is not None
        assert got.word == "hello"
        assert got.phonetic == "/test/"
        assert got.definition_cn == "测试词"

    def test_get_nonexistent_word(self, repo):
        """查询不存在的词应该返回 None。"""
        assert repo.get_word("nonexistent") is None

    def test_word_count(self, populated_repo):
        """词数应该等于插入的数量。"""
        assert populated_repo.word_count() == 3

    def test_get_words_by_level(self, populated_repo):
        """按等级筛选。"""
        cet4_words = populated_repo.get_words_by_level("cet4")
        assert len(cet4_words) == 2
        assert all(w.level == "cet4" for w in cet4_words)

        cet6_words = populated_repo.get_words_by_level("cet6")
        assert len(cet6_words) == 1

    def test_get_words_by_topic(self, populated_repo):
        """按话题标签搜索。"""
        food_words = populated_repo.get_words_by_topic("food")
        assert len(food_words) == 1
        assert food_words[0].word == "apple"

    def test_get_words_by_state(self, populated_repo):
        """按学习状态筛选。新插入的词默认状态是 UNKNOWN。"""
        unknown = populated_repo.get_words_by_state(VocabularyState.UNKNOWN)
        assert len(unknown) == 3

    def test_update_word_state(self, populated_repo):
        """更新学习状态后，查询应该返回新状态。"""
        assert populated_repo.update_word_state("apple", VocabularyState.INTRODUCED)
        # 验证：现在按 INTRODUCED 查应该找到 apple
        introduced = populated_repo.get_words_by_state(VocabularyState.INTRODUCED)
        assert any(w.word == "apple" for w in introduced)

    def test_update_nonexistent_word(self, repo):
        """更新不存在的词应该返回 False。"""
        result = repo.update_word_state("nobody", VocabularyState.MASTERED)
        assert result is False

    def test_empty_repo_count(self, repo):
        """空数据库词数应为 0。"""
        assert repo.word_count() == 0

    def test_learning_tables_created(self, repo):
        """新仓库应该包含掌握度表和学习事件表。"""
        mastery = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='word_mastery'"
        ).fetchone()
        events = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='learning_events'"
        ).fetchone()
        assert mastery is not None
        assert events is not None

    def test_update_and_get_word_mastery(self, populated_repo):
        """掌握度记录可以新增并读回。"""
        populated_repo.update_word_mastery(
            word="apple",
            mastery_score=35,
            seen_count=1,
            attempt_count=2,
            correct_count=1,
            wrong_count=1,
            last_quality=4,
        )
        mastery = populated_repo.get_word_mastery("apple")
        assert mastery["mastery_score"] == 35
        assert mastery["attempt_count"] == 2
        assert mastery["last_quality"] == 4

    def test_record_learning_event(self, populated_repo):
        """学习事件可以保存到 learning_events 表。"""
        populated_repo.record_learning_event(
            word="apple",
            event_type="correct_usage",
            quality=4,
            mastery_delta=15,
            user_text="I eat an apple.",
        )
        row = populated_repo._conn.execute(
            "SELECT * FROM learning_events WHERE word = ?", ("apple",)
        ).fetchone()
        assert row is not None
        assert row["event_type"] == "correct_usage"
        assert row["mastery_delta"] == 15
