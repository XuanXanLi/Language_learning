"""对话管理器 — Line C 总指挥。

核心理念：用户说中文词 → LLM 先翻译再回答 → 用户主动用出英文 → 系统追踪。

每轮对话流程：
  1. 提取用户消息中的中文词（焦点词）和英文 CET 词
  2. 构建 Prompt（中文焦点词优先，让 LLM 先翻译再回答）
  3. 调用 LLM 获取回复
  4. 扫描 LLM 回复（不做词汇追踪，仅记录上下文）
  5. 用户后续使用英文词 → 追踪 "你用过" → "复习中"
"""

import re
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import defaultdict

from PyQt5.QtCore import QObject, pyqtSignal

from ..domain.learning_event import LearningEventType
from ..domain.vocabulary_state import VocabularyState
from ..engine.learning_evaluator import LearningEvaluator
from ..engine.mastery_scorer import MasteryScorer
from ..engine.prompt_builder import PromptBuilder
from ..engine.srs_scheduler import SRSScheduler
from ..engine.target_word_tracker import TargetWordTracker
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

# 掌握阈值：用户主动使用同一词 ≥ N 次 → 进入 SRS 复习
MASTERY_THRESHOLD = 2


class ConversationManager(QObject):
    """对话总控制器。

    信号：
    - message_received: 有新消息 (text: str, is_user: bool)
    - status_changed:   状态变化 (status: str)
    - word_event:       词汇事件 (word: str, event: str, state: str)
                        event: "target" (AI翻译引入), "used" (用户使用),
                               "learning" (进入复习)
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
        self.evaluator = LearningEvaluator(
            llm=llm,
            use_llm=(getattr(llm, "name", "") == "CloudLLM"),
        )
        self.mastery_scorer = MasteryScorer()
        self.target_tracker = TargetWordTracker()

        #  ── 词汇追踪（会话级）──
        # 用户用过的 CET 英文词 → `{词: 使用次数}`
        self._words_used: Dict[str, int] = defaultdict(int)
        # 本次会话所有出现的 CET 词（按顺序，给 Prompt 用）
        self._recent_words: List[str] = []
        # 用户说过的中文词（焦点词）→ `{词: 首次出现轮数}`
        self._chinese_focus: Dict[str, int] = {}
        # 最近一轮的中文词（只给当前 Prompt 用，下一轮覆盖）
        self._current_chinese: List[str] = []
        # 已经发射过"进入SRS"信号的词，避免重复发射
        self._learning_emitted: Set[str] = set()
        # 本次会话学习总结用的数据
        self._target_words: Set[str] = set()
        self._correct_words: Set[str] = set()
        self._wrong_words: Dict[str, str] = {}
        self._pending_correction: Optional[dict] = None

    # ── 公开方法 ──

    def start_session(self, topic: str = "daily life"):
        """开始一个新对话会话。

        topic: 对话话题 (daily life / travel / work / food / technology...)
        """
        self.topic = topic
        self.turn_count = 0
        self.conversation_history = []
        self._words_used = defaultdict(int)
        self._recent_words = []
        self._chinese_focus = {}
        self._current_chinese = []
        self._learning_emitted = set()
        self._target_words = set()
        self._correct_words = set()
        self._wrong_words = {}
        self._pending_correction = None
        self.target_tracker.reset()
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

        # 2. 提取中文焦点词（只做 Prompt 输入，不发射事件）
        chinese_words = self._extract_chinese(text)
        if chinese_words:
            self.target_tracker.set_focus(chinese_words)
        for cw in chinese_words:
            if cw not in self._chinese_focus:
                self._chinese_focus[cw] = self.turn_count

        # 3. 扫描用户消息中的英文 CET 词汇
        user_words = self._scan_message(text, speaker="user")

        # 4. 切换到"思考中"
        self._update_status("thinking")

        # 5. 将用户消息加入对话历史
        self.conversation_history.append({"role": "user", "content": text})

        # 6. 构建 Prompt（中文焦点词优先）
        current_focus = chinese_words if chinese_words else self._current_chinese
        system_prompt = self.prompt_builder.build(
            recent_words=self._recent_words[-20:],
            chinese_words=current_focus,
            preferred_topic=self.topic,
        )
        session_ctx = self.prompt_builder.build_session_context(
            recent_words=self._recent_words[-10:],
            chinese_words=current_focus,
            turns_this_session=self.turn_count,
        )

        # 7. 调用 LLM
        response = self.llm.chat(
            system_prompt=system_prompt + "\n" + session_ctx,
            messages=self.conversation_history,
        )

        # 8. 显示 LLM 回复
        self.message_received.emit(response.text, False)

        # 9. 将 LLM 回复加入对话历史
        self.conversation_history.append({"role": "assistant", "content": response.text})

        # 10. 扫描 LLM 回复中的 CET 词汇（只记录上下文，不触发词汇事件）
        self._scan_llm_response(response.text)

        # 11. 评估用户输入是否命中当前目标词
        self._evaluate_learning_turn(text)

        # 12. 更新当前中文焦点（保留上一轮的，如果没有新的话）
        if chinese_words:
            self._current_chinese = chinese_words

        # 13. 语音输出（如果 TTS 可用）
        self._update_status("speaking")
        if self.tts and self.tts.is_available():
            self.tts.speak(response.text)
        self._update_status("idle")

        return response

    def get_session_summary(self) -> dict:
        """返回当前会话的词汇追踪摘要。"""
        mastery_scores = {}
        for word in sorted(self._target_words | set(self._words_used.keys())):
            mastery = self.repo.get_word_mastery(word)
            if mastery:
                mastery_scores[word] = mastery["mastery_score"]

        return {
            "topic": self.topic,
            "turns": self.turn_count,
            "chinese_focus": sorted(self._chinese_focus.keys()),
            "target_words": sorted(self._target_words),
            "words_used": dict(self._words_used),
            "correct_words": sorted(self._correct_words),
            "wrong_words": dict(self._wrong_words),
            "mastery_scores": mastery_scores,
            "review_due": self.srs.get_due_words(),
            "pending_correction": dict(self._pending_correction) if self._pending_correction else None,
        }

    def get_recent_words(self, limit: int = 20) -> List[str]:
        """获取最近遇到的 CET 词汇（给 Prompt 用）。"""
        seen = list(dict.fromkeys(self._recent_words))  # 去重但保持顺序
        return seen[-limit:]

    # ── 内部方法 ──

    def _extract_words(self, text: str) -> List[str]:
        """从句子中提取有意义的英文单词。

        - 转小写
        - 去掉标点符号
        - 过滤停用词和长度 ≤2 的词
        """
        cleaned = re.sub(r"[^\w\s']", " ", text.lower())
        raw_words = cleaned.split()

        return [
            w for w in raw_words
            if w not in STOP_WORDS and len(w) > 2
        ]

    @staticmethod
    def _extract_chinese(text: str) -> List[str]:
        """从句子中提取连续的中文字符块。

        "how to say 异性 in english so i can 概括 boy and girl"
        → ["异性", "概括"]
        """
        return re.findall(r"[一-鿿]+", text)

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
        """扫描用户消息中的英文 CET 词汇，更新状态。

        返回: 这条消息中在词库中命中的词列表
        """
        words = self._extract_words(text)
        if not words:
            return []

        lookup = self._batch_lookup(words)
        cet_words = [w for w, s in lookup.items() if s != "N/A"]

        for word in cet_words:
            current_state = lookup[word]
            self._record_word_used(word, current_state)

        return cet_words

    def _scan_llm_response(self, text: str):
        """扫描 LLM 回复中的 CET 词汇 → 发射 target 事件。"""
        words = self._extract_words(text)
        if not words:
            return
        lookup = self._batch_lookup(words)
        cet_words = [w for w, s in lookup.items() if s != "N/A"]
        for word in cet_words:
            self._recent_words.append(word)

        if self._current_chinese or self.target_tracker.has_active_targets():
            candidate_targets = self.target_tracker.ingest_assistant_response(text)
        else:
            candidate_targets = cet_words[:3]

        for word in candidate_targets:
            current_state = lookup.get(word)
            if current_state is None or current_state == "N/A":
                continue
            if current_state == "UNKNOWN":
                self.repo.update_word_state(word, VocabularyState.INTRODUCED)
            self._target_words.add(word)
            if word not in self._recent_words:
                self._recent_words.append(word)
            self._record_learning_progress(
                word=word,
                event_type=LearningEventType.INTRODUCED,
                quality=None,
            )
            self.word_event.emit(word, "target", "INTRODUCED")

    def _record_word_used(self, word: str, current_state: str):
        """用户在输入中使用了某个英文 CET 词。"""
        self._words_used[word] += 1
        use_count = self._words_used[word]
        evaluations = self.evaluator.evaluate(word, [word])
        quality = evaluations[0].quality if evaluations else 4

        if current_state in ("UNKNOWN", "INTRODUCED"):
            # 用户第一次主动用这个词 → ATTEMPTED
            self.repo.update_word_state(word, VocabularyState.ATTEMPTED)
            self._record_learning_progress(
                word=word,
                event_type=LearningEventType.CORRECT_USAGE,
                quality=quality,
            )
            self.word_event.emit(word, "used", "ATTEMPTED")
            self._recent_words.append(word)

        elif current_state == "ATTEMPTED" and use_count >= MASTERY_THRESHOLD:
            # 多次使用 → 进入 SRS 复习
            if word not in self._learning_emitted:
                self.repo.update_word_state(word, VocabularyState.LEARNING)
                self.srs.schedule(word, quality=quality)
                self._record_learning_progress(
                    word=word,
                    event_type=LearningEventType.REVIEW_PASSED,
                    quality=quality,
                )
                self.word_event.emit(word, "learning", "LEARNING")
                self._learning_emitted.add(word)

        elif current_state == "LEARNING":
            # 在复习中的词，记录一次正向使用
            self.srs.schedule(word, quality=5)
            self._record_learning_progress(
                word=word,
                event_type=LearningEventType.CORRECT_USAGE,
                quality=5,
            )

    def _record_learning_progress(
        self,
        word: str,
        event_type: LearningEventType,
        quality: Optional[int],
        user_text: str = "",
        ai_feedback: str = "",
        error_type: Optional[str] = None,
    ):
        """记录学习事件并更新掌握度。"""
        existing = self.repo.get_word_mastery(word) or {}
        current_score = existing.get("mastery_score", 0)
        new_score, delta = self.mastery_scorer.score_event(
            current_score=current_score,
            event_type=event_type,
            quality=quality,
        )
        now = datetime.now().isoformat()

        seen_count = existing.get("seen_count", 0)
        attempt_count = existing.get("attempt_count", 0)
        correct_count = existing.get("correct_count", 0)
        wrong_count = existing.get("wrong_count", 0)

        if event_type == LearningEventType.INTRODUCED:
            seen_count += 1
        if event_type in (
            LearningEventType.ATTEMPTED,
            LearningEventType.CORRECT_USAGE,
            LearningEventType.WRONG_USAGE,
            LearningEventType.REVIEW_PASSED,
            LearningEventType.REVIEW_FAILED,
        ):
            attempt_count += 1
        if event_type in (LearningEventType.CORRECT_USAGE, LearningEventType.REVIEW_PASSED):
            correct_count += 1
        if event_type in (LearningEventType.WRONG_USAGE, LearningEventType.REVIEW_FAILED):
            wrong_count += 1

        self.repo.update_word_mastery(
            word=word,
            mastery_score=new_score,
            seen_count=seen_count,
            attempt_count=attempt_count,
            correct_count=correct_count,
            wrong_count=wrong_count,
            last_seen_at=now,
            last_attempted_at=now if attempt_count else None,
            last_quality=quality,
        )
        self.repo.record_learning_event(
            word=word,
            event_type=event_type.value,
            quality=quality,
            mastery_delta=delta,
            user_text=user_text,
            ai_feedback=ai_feedback,
            error_type=error_type,
        )

    def _evaluate_learning_turn(self, user_text: str):
        """评估当前轮的学习表现，并更新掌握度与摘要。

        自由聊天阶段采用轻纠错策略：
        - 有 pending correction 时，强制评估并反馈这个词。
        - 没有 pending correction 时，只在用户主动尝试目标词时评分。
        - 不因为“没有用到目标词”立刻弹出纠错，避免正常聊天被打断。
        """
        target_words = self._collect_target_words(user_text)
        if not target_words:
            return

        self._target_words.update(target_words)
        results = self.evaluator.evaluate(user_text, target_words)

        for result in results[:1]:
            if result.attempted and result.correct:
                self._correct_words.add(result.word)
                if self._pending_correction and self._pending_correction.get("word") == result.word:
                    self._pending_correction = None
                self._record_learning_progress(
                    word=result.word,
                    event_type=LearningEventType.CORRECT_USAGE,
                    quality=result.quality,
                    user_text=user_text,
                    ai_feedback=result.correction or "",
                )
                if self.repo.update_word_state(result.word, VocabularyState.ATTEMPTED):
                    pass
                if self._words_used[result.word] >= MASTERY_THRESHOLD and result.word not in self._learning_emitted:
                    self.repo.update_word_state(result.word, VocabularyState.LEARNING)
                    self.srs.schedule(result.word, quality=result.quality)
                    self._record_learning_progress(
                        word=result.word,
                        event_type=LearningEventType.REVIEW_PASSED,
                        quality=result.quality,
                        user_text=user_text,
                        ai_feedback=result.correction or "",
                    )
                    self.word_event.emit(result.word, "learning", "LEARNING")
                    self._learning_emitted.add(result.word)

            elif result.attempted and not result.correct:
                self._wrong_words[result.word] = result.error_type or "wrong_usage"
                self._pending_correction = {
                    "word": result.word,
                    "correction": result.correction,
                    "explanation": result.explanation,
                }
                self._record_learning_progress(
                    word=result.word,
                    event_type=LearningEventType.WRONG_USAGE,
                    quality=result.quality,
                    user_text=user_text,
                    ai_feedback=result.correction or "",
                    error_type=result.error_type,
                )
                self._emit_correction_feedback(result)

            elif self._pending_correction:
                self._record_learning_progress(
                    word=result.word,
                    event_type=LearningEventType.ATTEMPTED,
                    quality=result.quality,
                    user_text=user_text,
                    ai_feedback=result.correction or "",
                    error_type=result.error_type,
                )
                self._emit_correction_feedback(result)

    def _collect_target_words(self, user_text: str) -> List[str]:
        """收集当前轮需要评估的目标词。"""
        if self._pending_correction:
            return [self._pending_correction["word"]]

        active_target = self.target_tracker.get_current_target()
        if active_target and active_target in self._extract_words(user_text):
            return [active_target]

        for word in sorted(self._target_words):
            if word in self._extract_words(user_text):
                return [word]

        return []

    def _emit_correction_feedback(self, result):
        """把纠错反馈显示到对话区。"""
        if not result.correction and not result.explanation:
            return

        lines = [f"[纠错] {result.word}"]
        if result.correction:
            lines.append(f"建议：{result.correction}")
        if result.explanation:
            lines.append(f"原因：{result.explanation}")
        feedback = "\n".join(lines)
        self.message_received.emit(feedback, False)

    def _get_db_state(self, word: str) -> str:
        """查询一个词在数据库中的当前状态。测试用。"""
        row = self.repo._conn.execute(
            "SELECT state FROM words WHERE word = ?", (word,)
        ).fetchone()
        return row["state"] if row else "N/A"

    def _update_status(self, status: str):
        """更新状态并通知 UI。"""
        self.status_changed.emit(status)
