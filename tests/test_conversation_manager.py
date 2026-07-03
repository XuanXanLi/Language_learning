"""ConversationManager 集成测试。

覆盖：
- 话题启动会话
- 用户消息中英文CET词汇扫描
- 中文焦点词提取
- 状态自动更新（用户使用→ATTEMPTED→LEARNING）
- 停用词过滤
- 批量数据库查询
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
        """LLM 回复中的 CET 词汇 → 记入 _recent_words + 发射 target 事件。"""
        custom_llm = MockLLM(responses=[
            "I love to explore new places and discover hidden gems."
        ])
        mgr = ConversationManager(llm=custom_llm, repository=manager.repo)
        mgr.start_session(topic="travel")
        mgr.handle_user_message("What do you like to do?")

        assert "explore" in mgr._recent_words
        assert "discover" in mgr._recent_words
        # 状态应该在数据库里变成 INTRODUCED
        words = mgr.repo.get_words_by_state(VocabularyState.INTRODUCED)
        assert any(w.word == "explore" for w in words)

    def test_user_skips_to_attempted(self, manager):
        """用户用了词库里有的词但从未被引入 → 直接 ATTEMPTED（跳级）"""
        manager.start_session(topic="daily life")
        manager.handle_user_message("I am very curious about science!")

        # 数据库里的状态应该变成 ATTEMPTED
        from line_c.domain.vocabulary_state import VocabularyState
        words = manager.repo.get_words_by_state(VocabularyState.ATTEMPTED)
        assert any(w.word == "curious" for w in words)

    def test_chinese_extraction(self, manager):
        """用户输入含中文词 → 正确提取。"""
        text = "how to say 异性 in english so i can 概括 boy and girl"
        chinese = manager._extract_chinese(text)
        assert "异性" in chinese
        assert "概括" in chinese
        assert len(chinese) == 2

    def test_chinese_focus_tracking(self, manager):
        """中文焦点词 → 记入 _chinese_focus（不做 UI 事件）。"""
        manager.start_session(topic="daily life")
        manager.handle_user_message("how to say 探索 in english?")

        assert "探索" in manager._chinese_focus

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

    def test_ai_target_word_event(self, manager, qapp):
        """AI 回复引入 CET 词 → 发射 target 信号。"""
        events = []

        def on_event(word, event, state):
            events.append((word, event, state))

        custom_llm = MockLLM(responses=["You seem curious about the world!"])
        mgr = ConversationManager(llm=custom_llm, repository=manager.repo)
        mgr.word_event.connect(on_event)
        mgr.start_session(topic="daily life")
        mgr.handle_user_message("Hello!")

        target_events = [e for e in events if e[1] == "target"]
        assert len(target_events) >= 1
        assert target_events[0][0] == "curious"

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

    def test_session_summary_includes_learning_report_fields(self, manager):
        """会话摘要应该包含学习报告需要的字段。"""
        manager.start_session(topic="daily life")
        manager.handle_user_message("I am curious about science.")

        summary = manager.get_session_summary()
        assert "target_words" in summary
        assert "correct_words" in summary
        assert "wrong_words" in summary
        assert "mastery_scores" in summary
        assert "review_due" in summary

    def test_pending_correction_clears_after_correct_retry(self, manager):
        """错误后重试正确，应清除 pending correction。"""
        manager.start_session(topic="daily life")
        manager._pending_correction = {"word": "curious", "correction": "Use curious.", "explanation": ""}
        manager._current_chinese = ["好奇"]

        manager.handle_user_message("I am curious about science.")

        assert manager._pending_correction is None
        assert "curious" in manager.get_session_summary()["correct_words"]

    def test_missing_target_emits_correction_feedback(self, manager, qapp):
        """有 pending correction 时，没有使用目标词应显示纠错提示。"""
        messages = []

        def on_message(text, is_user):
            messages.append((text, is_user))

        manager.message_received.connect(on_message)
        manager.start_session(topic="daily life")
        manager._pending_correction = {"word": "curious", "correction": "Use curious.", "explanation": ""}
        manager._target_words.add("curious")
        manager._current_chinese = ["好奇"]

        manager.handle_user_message("I like science.")

        ai_messages = [text for text, is_user in messages if not is_user]
        assert any("[纠错] curious" in text for text in ai_messages)
        assert manager._pending_correction["word"] == "curious"

    def test_free_chat_does_not_correct_missing_target(self, manager, qapp):
        """自由聊天中没用目标词时，不应立刻弹出纠错。"""
        messages = []

        def on_message(text, is_user):
            messages.append((text, is_user))

        manager.message_received.connect(on_message)
        manager.start_session(topic="daily life")
        manager._target_words.update({"curious", "discover", "explore"})
        manager.target_tracker._active_targets = ["curious", "discover", "explore"]

        manager.handle_user_message("I like science.")

        ai_messages = [text for text, is_user in messages if not is_user]
        assert not any(text.startswith("[纠错]") for text in ai_messages)
