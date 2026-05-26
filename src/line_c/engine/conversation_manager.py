"""VocaAI 风格的对话管理器 — Line C 总指挥。

核心理念：不预设"今天学哪几个词"。用户在自然对话中遇到和使用的
所有 CET 词汇都由系统在后台追踪。

每轮对话流程：
  1. 扫描用户消息中的 CET 词汇 → 更新状态
  2. 构建 Prompt（话题驱动，含最近遇到的词）
  3. 调用 LLM 获取回复
  4. 扫描 LLM 回复中的 CET 词汇 → 更新状态
  5. 定期评估：哪些词可以进入 SRS 复习、哪些是薄弱词
"""

import re
from typing import Dict, List, Set, Optional
from collections import defaultdict

from PyQt5.QtCore import QObject, pyqtSignal

from ..domain.vocabulary_state import VocabularyState
from ..engine.prompt_builder import PromptBuilder
from ..engine.srs_scheduler import SRSScheduler
from ..llm.base import BaseLLM
from ..tts.base import BaseTTS


# ── 停用词表：这些常见虚词不作为"英语词汇学习"的目标 ──
STOP_WORDS: Set[str] = {
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself",
    "he", "him", "his", "she", "her", "hers", "it", "its", "we", "us",
    "our", "ours", "they", "them", "their", "theirs",
    "a", "an", "the", "this", "that", "these", "those",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might",
    "must", "ought", "need", "dare",
    "to", "for", "of", "in", "on", "at", "by", "with", "from",
    "up", "down", "out", "off", "over", "under", "about", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "and", "or", "but", "if", "because", "as", "until", "while",
    "not", "no", "nor", "so", "than", "too", "very", "just",
    "also", "now", "then", "here", "there", "when", "where", "why", "how",
    "all", "both", "each", "few", "more", "most", "other", "some", "such",
    "only", "own", "same", "still", "well", "really", "even", "much",
    "yes", "yeah", "nope", "hi", "hey", "hello", "oh", "ok", "okay",
    "please", "thanks", "thank", "sorry", "goodbye", "bye",
    "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "couldn't",
    "isn't", "aren't", "wasn't", "weren't", "haven't", "hasn't", "hadn't",
    "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
    "i'll", "you'll", "he'll", "she'll", "we'll", "they'll",
    "i've", "you've", "we've", "they've", "i'd", "you'd", "he'd", "she'd",
    "what's", "that's", "there's", "here's", "let's",
}

# 评估间隔：每 N 轮触发一次词汇评估
EVALUATION_INTERVAL = 5
# 薄弱词阈值：见过超过 N 轮还没用过 → 标记为薄弱词
WEAK_WORD_THRESHOLD = 5
# 掌握阈值：用户主动使用同一词 ≥ N 次 → 进入 LEARNING
MASTERY_THRESHOLD = 2


class ConversationManager(QObject):
    """对话总控制器。

    信号：
    - message_received: 有新消息 (text: str, is_user: bool)
    - status_changed:   状态变化 (status: str)
    - word_event:       词汇事件 (word: str, event: str, state: str)
                        event: "seen" (LLM引入), "used" (用户使用),
                               "learning" (进入复习), "weak" (标记薄弱)
    """

    message_received = pyqtSignal(str, bool)
    status_changed = pyqtSignal(str)
    word_event = pyqtSignal(str, str, str)

    def __init__(
        self,
        llm: BaseLLM,
        repository,
        prompt_builder: Optional[PromptBuilder] = None,
        tts: Optional[BaseTTS] = None,
    ):
        super().__init__()
        self.llm = llm
        self.repo = repository
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.tts = tts

        # 会话状态
        self.topic: str = "daily life"
        self.turn_count: int = 0
        self.conversation_history: List[dict] = []

        # 引擎
        self.srs = SRSScheduler()

        # ── 词汇追踪（会话级）──
        # LLM 用过的 CET 词 → `{词: 首次出现轮数}`
        self._words_seen: Dict[str, int] = {}
        # 用户用过的 CET 词 → `{词: 使用次数}`
        self._words_used: Dict[str, int] = defaultdict(int)
        # 本次会话所有遇到的 CET 词（按顺序，用于 Prompt）
        self._recent_words: List[str] = []
        # 薄弱词：见过但用户一直没用过的
        self._weak_words: List[str] = []
        # 已经发射过"进入SRS"信号的词，避免重复发射
        self._learning_emitted: Set[str] = set()

    # ── 公开方法 ──

    def start_session(self, topic: str = "daily life"):
        """开始一个新对话会话。

        topic: 对话话题 (daily life / travel / work / food / technology...)
        """
        self.topic = topic
        self.turn_count = 0
        self.conversation_history = []
        self._words_seen = {}
        self._words_used = defaultdict(int)
        self._recent_words = []
        self._weak_words = []
        self._learning_emitted = set()
        self._update_status("idle")

    def handle_user_message(self, text: str):
        """处理用户输入——每轮对话的核心入口。

        返回 LLMResponse，同时通过信号通知 UI。
        """
        if not text.strip():
            return

        # 1. 显示用户消息
        self.message_received.emit(text, True)
        self.turn_count += 1

        # 2. 扫描用户消息中的 CET 词汇
        user_words = self._scan_message(text, speaker="user")

        # 3. 切换到"思考中"
        self._update_status("thinking")

        # 4. 将用户消息加入对话历史
        self.conversation_history.append({"role": "user", "content": text})

        # 5. 构建 Prompt
        system_prompt = self.prompt_builder.build(
            recent_words=self._recent_words[-20:],
            weak_words=self._get_current_weak_words(),
            preferred_topic=self.topic,
        )
        session_ctx = self.prompt_builder.build_session_context(
            recent_words=self._recent_words[-10:],
            turns_this_session=self.turn_count,
        )

        # 6. 调用 LLM（现在 LLM 能看到用户刚发的消息了）
        response = self.llm.chat(
            system_prompt=system_prompt + "\n" + session_ctx,
            messages=self.conversation_history,
        )

        # 7. 显示 LLM 回复
        self.message_received.emit(response.text, False)

        # 8. 将 LLM 回复加入对话历史
        self.conversation_history.append({"role": "assistant", "content": response.text})

        # 9. 扫描 LLM 回复中的 CET 词汇
        self._scan_message(response.text, speaker="llm")

        # 10. 定期评估
        if self.turn_count % EVALUATION_INTERVAL == 0:
            self._evaluate_progress()

        # 11. 语音输出（如果 TTS 可用）
        self._update_status("speaking")
        if self.tts and self.tts.is_available():
            self.tts.speak(response.text)
        self._update_status("idle")

        return response

    def get_session_summary(self) -> dict:
        """返回当前会话的词汇追踪摘要。"""
        return {
            "topic": self.topic,
            "turns": self.turn_count,
            "words_seen": sorted(self._words_seen.keys()),
            "words_used": dict(self._words_used),
            "weak_words": self._weak_words,
        }

    def get_recent_words(self, limit: int = 20) -> List[str]:
        """获取最近遇到的 CET 词汇（给 Prompt 用）。"""
        seen = list(dict.fromkeys(self._recent_words))  # 去重但保持顺序
        return seen[-limit:]

    # ── 内部方法 ──

    def _extract_words(self, text: str) -> List[str]:
        """从句子中提取有意义的单词。

        - 转小写
        - 去掉标点符号
        - 过滤停用词和长度 ≤2 的词
        """
        # 去掉标点
        cleaned = re.sub(r"[^\w\s']", " ", text.lower())
        raw_words = cleaned.split()

        return [
            w for w in raw_words
            if w not in STOP_WORDS and len(w) > 2
        ]

    def _batch_lookup(self, words: List[str]) -> Dict[str, str]:
        """批量查询一组词在词库中的状态。

        一条 SQL 搞定，不是 N 条。
        输入: ["curious", "hiking", "explore"]
        返回: {"curious": "UNKNOWN", "hiking": "N/A", "explore": "UNKNOWN"}
              "N/A" 表示词库中没有这个词
        """
        if not words:
            return {}

        placeholders = ",".join(["?"] * len(words))
        sql = f"SELECT word, state FROM words WHERE word IN ({placeholders})"
        rows = self.repo._conn.execute(sql, words).fetchall()

        db_words = {row["word"]: row["state"] for row in rows}
        # 不在 DB 中的词标记为 "N/A"
        return {w: db_words.get(w, "N/A") for w in words}

    def _scan_message(self, text: str, speaker: str) -> List[str]:
        """扫描一条消息中出现的 CET 词汇，并更新状态。

        speaker: "user" 或 "llm"
        返回: 这条消息中在词库中命中的词列表
        """
        words = self._extract_words(text)
        if not words:
            return []

        lookup = self._batch_lookup(words)
        cet_words = [w for w, s in lookup.items() if s != "N/A"]

        for word in cet_words:
            current_state = lookup[word]

            if speaker == "llm":
                # LLM 用了这个词 → 用户"见过"
                self._record_word_seen(word, current_state)
            else:
                # 用户用了这个词 → "试过"
                self._record_word_used(word, current_state)

        return cet_words

    def _record_word_seen(self, word: str, current_state: str):
        """LLM 在回复中使用了某个 CET 词。"""
        if word not in self._words_seen:
            self._words_seen[word] = self.turn_count
        self._recent_words.append(word)

        if current_state == "UNKNOWN":
            # 第一次见 → INTRODUCED
            self.repo.update_word_state(word, VocabularyState.INTRODUCED)
            self.word_event.emit(word, "seen", "INTRODUCED")

    def _record_word_used(self, word: str, current_state: str):
        """用户在输入中使用了某个 CET 词。"""
        self._words_used[word] += 1
        use_count = self._words_used[word]

        if current_state == "UNKNOWN":
            # 用户自证认识 → 跳过 INTRODUCED，直接 ATTEMPTED
            self.repo.update_word_state(word, VocabularyState.ATTEMPTED)
            self.word_event.emit(word, "used", "ATTEMPTED")
            # 同时记入 seen 列表（虽然跳级了）
            if word not in self._words_seen:
                self._words_seen[word] = self.turn_count
            self._recent_words.append(word)

        elif current_state == "INTRODUCED":
            # 用户学以致用 → ATTEMPTED
            self.repo.update_word_state(word, VocabularyState.ATTEMPTED)
            self.word_event.emit(word, "used", "ATTEMPTED")

        elif current_state == "ATTEMPTED" and use_count >= MASTERY_THRESHOLD:
            # 多次正确使用 → 进入 SRS 复习（不重复发射信号）
            if word not in self._learning_emitted:
                self.repo.update_word_state(word, VocabularyState.LEARNING)
                self.srs.schedule(word, quality=4)
                self.word_event.emit(word, "learning", "LEARNING")
                self._learning_emitted.add(word)

        elif current_state == "LEARNING":
            # 在复习中的词，记录一次正向使用 → SRS review
            self.srs.schedule(word, quality=5)

    def _evaluate_progress(self):
        """定期评估：检测薄弱词。"""
        current_turn = self.turn_count

        # 找出"见过超过 N 轮但用户从未用过"的词 → 薄弱词
        for word, first_seen_turn in self._words_seen.items():
            if word in self._words_used:
                continue  # 用户已经用过了，不是薄弱词
            if (
                current_turn - first_seen_turn >= WEAK_WORD_THRESHOLD
                and word not in self._weak_words
            ):
                self._weak_words.append(word)
                self.word_event.emit(word, "weak", self._get_db_state(word))

    def _get_current_weak_words(self) -> List[str]:
        """获取当前的薄弱词列表。"""
        result = []
        for word, first_seen in self._words_seen.items():
            if word not in self._words_used:
                if self.turn_count - first_seen >= WEAK_WORD_THRESHOLD:
                    result.append(word)
        return result

    def _get_db_state(self, word: str) -> str:
        """查询一个词在数据库中的当前状态。"""
        row = self.repo._conn.execute(
            "SELECT state FROM words WHERE word = ?", (word,)
        ).fetchone()
        return row["state"] if row else "N/A"

    def _update_status(self, status: str):
        """更新状态并通知 UI。"""
        self.status_changed.emit(status)
