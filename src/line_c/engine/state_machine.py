"""词汇状态机（State Machine）。

状态机是一种设计模式：定义一组"状态"和"触发条件"，
当条件满足时自动迁移到下一个状态。

这个模块管理单个词的完整学习生命周期。
"""

from datetime import datetime
from typing import List, Optional

from ..domain.vocabulary_state import VocabularyState, can_transition, describe_state
from ..domain.learning_record import LearningRecord


class VocabularyStateMachine:
    """管理一个词汇的学习状态迁移。

    用法：
        sm = VocabularyStateMachine(word="abandon")
        sm.try_transition(VocabularyState.INTRODUCED)  # → True（合法）
        sm.try_transition(VocabularyState.MASTERED)     # → False（非法跳跃）

    注意：这个类不依赖数据库。状态的持久化由上层（ConversationManager）
    负责，状态机本身只做"这个迁移合法吗？"的判断。
    """

    def __init__(self, word: str, initial_state: VocabularyState = VocabularyState.UNKNOWN):
        """
        word:          哪个词
        initial_state: 初始状态（新词默认 UNKNOWN）
        """
        self.word = word
        self.current_state = initial_state
        self._history: List[LearningRecord] = []  # 状态变更历史

    def try_transition(
        self,
        to_state: VocabularyState,
        session_id: Optional[str] = None,
        quality: Optional[int] = None,
    ) -> bool:
        """尝试将词汇迁移到新状态。

        返回 True 表示迁移成功，False 表示不合法。

        参数：
        - to_state:   目标状态
        - session_id: 哪个对话会话触发的（可选）
        - quality:    用户表现评分 0-5（仅复习场景使用）
        """
        if not can_transition(self.current_state, to_state):
            return False

        # 记录这次迁移
        record = LearningRecord(
            word=self.word,
            from_state=self.current_state,
            to_state=to_state,
            timestamp=datetime.now(),
            session_id=session_id,
            quality=quality,
        )
        self._history.append(record)
        self.current_state = to_state
        return True

    @property
    def history(self) -> List[LearningRecord]:
        """返回状态变更的完整历史。"""
        return list(self._history)

    def last_transition(self) -> Optional[LearningRecord]:
        """返回最近一次迁移记录，没有则返回 None。"""
        return self._history[-1] if self._history else None

    def describe(self) -> str:
        """返回当前状态的中文描述。"""
        return describe_state(self.current_state)

    def __repr__(self) -> str:
        return f"VocabularyStateMachine(word={self.word!r}, state={self.current_state.name})"


class StateMachineGroup:
    """管理一组词汇的状态机——一次对话可能涉及多个词。

    用法：
        group = StateMachineGroup(["apple", "banana", "cherry"])
        group.introduce("apple")       # UNKNOWN → INTRODUCED
        group.attempt("apple")         # INTRODUCED → ATTEMPTED
        group.start_learning("apple")  # ATTEMPTED → LEARNING
        group.master("apple")          # LEARNING → MASTERED
    """

    def __init__(self, words: List[str]):
        self._machines = {
            word: VocabularyStateMachine(word) for word in words
        }

    def get(self, word: str) -> Optional[VocabularyStateMachine]:
        """获取某个词的状态机。找不到返回 None。"""
        return self._machines.get(word)

    def all_states(self) -> dict:
        """返回 {词: 当前状态} 的字典。"""
        return {word: sm.current_state for word, sm in self._machines.items()}

    # ── 便捷方法：一次迁移一个词 ──

    def _transition(self, word: str, to_state: VocabularyState, **kwargs) -> bool:
        sm = self._machines.get(word)
        if sm is None:
            return False
        return sm.try_transition(to_state, **kwargs)

    def introduce(self, word: str, **kwargs) -> bool:
        """标记一个词被 LLM 引入对话。UNKNOWN → INTRODUCED。"""
        return self._transition(word, VocabularyState.INTRODUCED, **kwargs)

    def attempt(self, word: str, **kwargs) -> bool:
        """用户尝试使用该词。INTRODUCED → ATTEMPTED。"""
        return self._transition(word, VocabularyState.ATTEMPTED, **kwargs)

    def start_learning(self, word: str, **kwargs) -> bool:
        """进入 SRS 复习队列。ATTEMPTED → LEARNING。"""
        return self._transition(word, VocabularyState.LEARNING, **kwargs)

    def master(self, word: str, **kwargs) -> bool:
        """判定为已掌握。LEARNING → MASTERED。"""
        return self._transition(word, VocabularyState.MASTERED, **kwargs)

    def fallback(self, word: str, from_state: VocabularyState, **kwargs) -> bool:
        """回退到前一个状态（用户用错了或复习失败）。"""
        if from_state == VocabularyState.ATTEMPTED:
            return self._transition(word, VocabularyState.INTRODUCED, **kwargs)
        if from_state == VocabularyState.LEARNING:
            return self._transition(word, VocabularyState.ATTEMPTED, **kwargs)
        return False
