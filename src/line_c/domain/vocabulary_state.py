from enum import Enum, auto
from typing import Dict, Set, FrozenSet


class VocabularyState(Enum):
    """词汇学习五阶段。

    Enum（枚举）是一组有名字的常量。比如写 VocabularyState.MASTERED
    比写数字 4 更可读、更不容易出错。

    auto() 意思是"自动给我一个不重复的值"，不关心具体数字。
    """
    UNKNOWN = auto()     # 未学过 —— 词库里但用户还没接触
    INTRODUCED = auto()  # 已引入 —— 对话中 LLM 用过这个词
    ATTEMPTED = auto()   # 已尝试 —— 用户在回复中使用过这个词
    LEARNING = auto()    # 学习中 —— 进入 SRS 间隔复习队列
    MASTERED = auto()    # 已掌握 —— SRS 判定牢固掌握


# 合法的状态迁移规则：从某个状态可以跳转到哪些状态
# frozenset 是不可变的集合，用作字典的 key 更安全
VALID_TRANSITIONS: Dict[VocabularyState, FrozenSet[VocabularyState]] = {
    VocabularyState.UNKNOWN: frozenset({
        VocabularyState.INTRODUCED,
    }),
    VocabularyState.INTRODUCED: frozenset({
        VocabularyState.ATTEMPTED,
    }),
    VocabularyState.ATTEMPTED: frozenset({
        VocabularyState.INTRODUCED,  # 用得不好，回退
        VocabularyState.LEARNING,
    }),
    VocabularyState.LEARNING: frozenset({
        VocabularyState.ATTEMPTED,   # 复习失败，回退
        VocabularyState.MASTERED,
    }),
    VocabularyState.MASTERED: frozenset({
        VocabularyState.LEARNING,    # 长期不用，退化
    }),
}


def can_transition(from_state: VocabularyState, to_state: VocabularyState) -> bool:
    """检查一个状态迁移是否合法。"""
    if from_state not in VALID_TRANSITIONS:
        return False
    return to_state in VALID_TRANSITIONS[from_state]


def describe_state(state: VocabularyState) -> str:
    """返回状态的中文描述。"""
    descriptions = {
        VocabularyState.UNKNOWN: "未学",
        VocabularyState.INTRODUCED: "见过",
        VocabularyState.ATTEMPTED: "试过",
        VocabularyState.LEARNING: "学习中",
        VocabularyState.MASTERED: "已掌握",
    }
    return descriptions.get(state, "未知")
