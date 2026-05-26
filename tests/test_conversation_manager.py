"""ConversationManager 集成测试（VocaAI 风格）。

覆盖：
- 话题启动会话
- 全量扫描用户/LLM消息中的CET词汇
- 状态自动更新（UNKNOWN→INTRODUCED→ATTEMPTED→LEARNING）
- 停用词过滤
- 批量数据库查询
- 薄弱词检测
- 信号发射
"""
import pytest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from line_c.domain.vocabulary_state import VocabularyState
from line_c.llm.mock_llm import MockLLM
from line_c.engine.vocabulary_repository import VocabularyRepository
from line_c.engine.conversation_manager import ConversationManager, STOP_WORDS


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


# ── 测试夹具 ──

@pytest.fixture
def repo():
    """内存数据库，预装测试 CET 词汇。"""
    r = VocabularyRepository(Path(":memory:"))
    from line_c.domain.word import Word
    words = [
        Word(word="curious", phonetic="/t/", part_of_speech="adj.",
             definition_en="eager to know", definition_cn="好奇的",
             examples=[], level="cet4", topic_tags=["emotion"], difficulty=0.3),
        Word(word="discover", phonetic="/t/", part_of_speech="v.",
             definition_en="find something new", definition_cn="发现",
             examples=[], level="cet4", topic_tags=["education"], difficulty=0.3),
        Word(word="explore", phonetic="/t/", part_of_speech="v.",
             definition_en="travel to discover", definition_cn="探索",
             examples=[], level="cet4", topic_tags=["travel"], difficulty=0.3),
        Word(word="energetic", phonetic="/t/", part_of_speech="adj.",
             definition_en="full of energy", definition_cn="精力充沛的",
             examples=[], level="cet4", topic_tags=["health"], difficulty=0.3),
        Word(word="hiking", phonetic="/t/", part_of_speech="n.",
             definition_en="walking in nature", definition_cn="徒步旅行",
             examples=[], level="cet4", topic_tags=["travel"], difficulty=0.3),
        Word(word="endurance", phonetic="/t/", part_of_speech="n.",
             definition_en="ability to endure", definition_cn="耐力",
             examples=[], level="cet6", topic_tags=["health"], difficulty=0.5),
    ]
    r.add_words(words)
    return r


@pytest.fixture
def manager(qapp, repo):
    llm = MockLLM()
    return ConversationManager(llm=llm, repository=repo)


# ── 停用词测试 ──

class TestStopWords:

    def test_common_stop_words_filtered(self):
        """常见虚词应该在停用词表中。"""
        assert "the" in STOP_WORDS
        assert "is" in STOP_WORDS
        assert "i" in STOP_WORDS
        assert "and" in STOP_WORDS

    def test_meaningful_words_not_filtered(self):
        """实义词不在停用词表中。"""
        assert "curious" not in STOP_WORDS
        assert "discover" not in STOP_WORDS
        assert "hiking" not in STOP_WORDS


# ── 词提取测试 ──

class TestWordExtraction:

    def test_extracts_meaningful_words(self, manager):
        words = manager._extract_words("I am curious about hiking")
        assert "curious" in words
        assert "hiking" in words
        assert "about" not in words  # 停用词

    def test_strips_punctuation(self, manager):
        words = manager._extract_words("Let's explore! It's amazing, right?")
        assert "explore" in words
        assert "amazing" in words
        assert "let's" not in words  # 带撇号的缩略词

    def test_filters_short_words(self, manager):
        words = manager._extract_words("Is it a go or no?")
        # "go" 长度=2，被过滤；"it", "a", "is", "or", "no" 是停用词
        assert len(words) == 0

    def test_empty_sentence(self, manager):
        assert manager._extract_words("") == []


# ── 批量查询测试 ──

class TestBatchLookup:

    def test_finds_words_in_db(self, manager):
        lookup = manager._batch_lookup(["curious", "discover"])
        assert lookup["curious"] == "UNKNOWN"
        assert lookup["discover"] == "UNKNOWN"

    def test_marks_unknown_words_as_na(self, manager):
        lookup = manager._batch_lookup(["obviously_not_a_word", "curious"])
        assert lookup["obviously_not_a_word"] == "N/A"
        assert lookup["curious"] == "UNKNOWN"

    def test_empty_list(self, manager):
        assert manager._batch_lookup([]) == {}


# ── ConversationManager 集成测试 ──

class TestConversationManager:

    def test_start_session_sets_topic(self, manager):
        manager.start_session(topic="travel")
        assert manager.topic == "travel"
        assert manager.turn_count == 0

    def test_handle_message_scans_user_words(self, manager):
        """用户输入包含 CET 词汇 → 应该被追踪。"""
        manager.start_session(topic="daily life")
        manager.handle_user_message("I am curious about hiking!")

        assert "curious" in manager._words_used
        assert "hiking" in manager._words_used

    def test_handle_message_scans_llm_response(self, manager):
        """LLM 回复包含 CET 词汇 → 应该被追踪。"""
        # 用定制的 MockLLM，确保回复包含已知词
        custom_llm = MockLLM(responses=[
            "I love to explore new places and discover hidden gems."
        ])
        mgr = ConversationManager(llm=custom_llm, repository=manager.repo)
        mgr.start_session(topic="travel")
        mgr.handle_user_message("What do you like to do?")

        assert "explore" in mgr._words_seen
        assert "discover" in mgr._words_seen

    def test_user_skips_to_attempted(self, manager):
        """用户用了词库里有的词但从未被引入 → 直接 ATTEMPTED（跳级）"""
        manager.start_session(topic="daily life")
        manager.handle_user_message("I am very curious about science!")

        # 数据库里的状态应该变成 ATTEMPTED
        from line_c.domain.vocabulary_state import VocabularyState
        words = manager.repo.get_words_by_state(VocabularyState.ATTEMPTED)
        assert any(w.word == "curious" for w in words)

    def test_llm_introduces_word(self, manager):
        """LLM 用了未知词 → INTRODUCED。"""
        custom_llm = MockLLM(responses=["You seem curious about the world!"])
        mgr = ConversationManager(llm=custom_llm, repository=manager.repo)
        mgr.start_session(topic="daily life")
        mgr.handle_user_message("Hello!")

        words = mgr.repo.get_words_by_state(VocabularyState.INTRODUCED)
        assert any(w.word == "curious" for w in words)

    def test_multiple_uses_trigger_learning(self, manager):
        """用户多次正确使用同一个词 → 进入 LEARNING。"""
        manager.start_session(topic="daily life")

        # 第一次用 → ATTEMPTED
        manager.handle_user_message("I am curious about English.")
        state_after_1 = manager._get_db_state("curious")
        assert state_after_1 == "ATTEMPTED"

        # 第二次用 → LEARNING
        manager.handle_user_message("Also curious about Chinese culture.")
        state_after_2 = manager._get_db_state("curious")
        assert state_after_2 == "LEARNING"

    def test_weak_word_detection(self, manager):
        """LLM 引入了词但用户一直不用 → 薄弱词。

        注意：WEAK_WORD_THRESHOLD=5，且在每 5 轮时触发评估。
        所以需要 >=10 轮才能确保在某次评估中 轮数差 >= 5。
        """
        custom_llm = MockLLM(responses=[
            "I think you'd love to explore new things.",
        ] * 15)  # 所有回复都含 "explore"
        mgr = ConversationManager(llm=custom_llm, repository=manager.repo)
        mgr.start_session(topic="daily life")

        for i in range(10):
            mgr.handle_user_message("OK, tell me something else.")

        assert "explore" in mgr._weak_words

    def test_word_event_signals(self, manager, qapp):
        """word_event 信号应该正确发射。"""
        events = []

        def on_event(word, event, state):
            events.append((word, event, state))

        manager.word_event.connect(on_event)
        manager.start_session(topic="daily life")

        # 用户用了 CET 词
        manager.handle_user_message("I want to discover new music!")
        # 应该至少有一个 "used" 事件
        used_events = [e for e in events if e[1] == "used"]
        assert len(used_events) >= 1

    def test_conversation_history(self, manager):
        """对话历史正确记录。"""
        manager.start_session(topic="travel")
        manager.handle_user_message("I love traveling!")

        assert len(manager.conversation_history) == 2
        assert manager.conversation_history[0]["role"] == "user"
        assert manager.conversation_history[1]["role"] == "assistant"

    def test_session_summary(self, manager):
        """会话摘要包含所有追踪数据。"""
        manager.start_session(topic="travel")
        manager.handle_user_message("I want to explore mountains!")

        summary = manager.get_session_summary()
        assert summary["topic"] == "travel"
        assert summary["turns"] == 1
        assert "explore" in summary["words_used"]

    def test_recent_words_ordered(self, manager):
        """最近遇到的词按顺序排列。"""
        custom_llm = MockLLM(responses=[
            "I'm curious about that.",
            "Let's discover together.",
        ])
        mgr = ConversationManager(llm=custom_llm, repository=manager.repo)
        mgr.start_session(topic="daily life")

        mgr.handle_user_message("Hi!")
        mgr.handle_user_message("Tell me more!")

        recent = mgr.get_recent_words()
        assert recent[0] == "curious"
        assert recent[1] == "discover"
