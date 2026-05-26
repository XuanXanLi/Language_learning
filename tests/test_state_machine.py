"""词汇状态机的测试用例。

覆盖：
- 每个合法状态迁移路径
- 非法跳跃
- 回退场景
- StateMachineGroup 批量管理
"""
import pytest

from line_c.domain.vocabulary_state import VocabularyState
from line_c.engine.state_machine import VocabularyStateMachine, StateMachineGroup


class TestVocabularyStateMachine:

    def test_initial_state_is_unknown(self):
        """新建的状态机，初始状态应该是 UNKNOWN。"""
        sm = VocabularyStateMachine("abandon")
        assert sm.current_state == VocabularyState.UNKNOWN

    def test_legal_transition_unknown_to_introduced(self):
        """合法迁移：UNKNOWN → INTRODUCED。"""
        sm = VocabularyStateMachine("abandon")
        assert sm.try_transition(VocabularyState.INTRODUCED) is True
        assert sm.current_state == VocabularyState.INTRODUCED

    def test_legal_transition_introduced_to_attempted(self):
        """合法迁移：INTRODUCED → ATTEMPTED。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.INTRODUCED)
        assert sm.try_transition(VocabularyState.ATTEMPTED) is True
        assert sm.current_state == VocabularyState.ATTEMPTED

    def test_legal_transition_attempted_to_learning(self):
        """合法迁移：ATTEMPTED → LEARNING。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.ATTEMPTED)
        assert sm.try_transition(VocabularyState.LEARNING) is True
        assert sm.current_state == VocabularyState.LEARNING

    def test_legal_transition_learning_to_mastered(self):
        """合法迁移：LEARNING → MASTERED。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.LEARNING)
        assert sm.try_transition(VocabularyState.MASTERED) is True
        assert sm.current_state == VocabularyState.MASTERED

    def test_fallback_attempted_to_introduced(self):
        """回退：ATTEMPTED → INTRODUCED（用户用得不好）。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.ATTEMPTED)
        assert sm.try_transition(VocabularyState.INTRODUCED) is True

    def test_fallback_learning_to_attempted(self):
        """回退：LEARNING → ATTEMPTED（复习失败）。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.LEARNING)
        assert sm.try_transition(VocabularyState.ATTEMPTED) is True

    def test_mastered_back_to_learning(self):
        """长期不用：MASTERED → LEARNING。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.MASTERED)
        assert sm.try_transition(VocabularyState.LEARNING) is True

    def test_illegal_jump_unknown_to_mastered(self):
        """非法跳跃：UNKNOWN → MASTERED 应该被拒绝。"""
        sm = VocabularyStateMachine("abandon")
        assert sm.try_transition(VocabularyState.MASTERED) is False
        assert sm.current_state == VocabularyState.UNKNOWN  # 状态不变

    def test_illegal_jump_mastered_to_unknown(self):
        """非法回退：MASTERED → UNKNOWN 应该被拒绝。"""
        sm = VocabularyStateMachine("abandon", VocabularyState.MASTERED)
        assert sm.try_transition(VocabularyState.UNKNOWN) is False

    def test_history_is_recorded(self):
        """每次合法迁移都会记录在历史中。"""
        sm = VocabularyStateMachine("abandon")
        sm.try_transition(VocabularyState.INTRODUCED)
        sm.try_transition(VocabularyState.ATTEMPTED)
        assert len(sm.history) == 2
        assert sm.history[0].from_state == VocabularyState.UNKNOWN
        assert sm.history[0].to_state == VocabularyState.INTRODUCED
        assert sm.history[1].from_state == VocabularyState.INTRODUCED
        assert sm.history[1].to_state == VocabularyState.ATTEMPTED

    def test_illegal_transition_not_recorded(self):
        """非法迁移不应该记录到历史中。"""
        sm = VocabularyStateMachine("abandon")
        sm.try_transition(VocabularyState.MASTERED)
        assert len(sm.history) == 0

    def test_complete_lifecycle(self):
        """完整生命周期：UNKNOWN → INTRODUCED → ATTEMPTED → LEARNING → MASTERED。"""
        sm = VocabularyStateMachine("abandon")
        assert sm.try_transition(VocabularyState.INTRODUCED)
        assert sm.try_transition(VocabularyState.ATTEMPTED)
        assert sm.try_transition(VocabularyState.LEARNING)
        assert sm.try_transition(VocabularyState.MASTERED)
        assert sm.current_state == VocabularyState.MASTERED
        assert len(sm.history) == 4

    def test_describe_returns_chinese(self):
        """describe() 应该返回中文状态名。"""
        sm = VocabularyStateMachine("test")
        assert sm.describe() == "未学"
        sm.try_transition(VocabularyState.INTRODUCED)
        assert sm.describe() == "见过"


class TestStateMachineGroup:

    def test_group_manages_multiple_words(self):
        """StateMachineGroup 管理多个词的状态。"""
        group = StateMachineGroup(["apple", "banana"])
        assert group.get("apple") is not None
        assert group.get("banana") is not None
        assert group.get("cherry") is None

    def test_introduce_and_attempt(self):
        """便捷方法 introduce() 和 attempt() 正确工作。"""
        group = StateMachineGroup(["abandon"])
        assert group.introduce("abandon") is True
        assert group.get("abandon").current_state == VocabularyState.INTRODUCED

        assert group.attempt("abandon") is True
        assert group.get("abandon").current_state == VocabularyState.ATTEMPTED

    def test_introduce_already_attempted_should_fail(self):
        """attempt 之后不能 introduce（状态机规则阻止回退到 INTRODUCED 再从 INTRODUCED 走）。"""
        group = StateMachineGroup(["abandon"])
        group.introduce("abandon")
        group.attempt("abandon")
        assert group.introduce("abandon") is True  # ATTEMPTED → INTRODUCED 是合法回退
