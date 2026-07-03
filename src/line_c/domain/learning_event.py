"""学习事件数据结构。

这个模块只定义数据，不依赖数据库、不依赖 Qt。
用于记录 VocaAI 风格学习闭环中发生过的事情：
- AI 引入目标词
- 用户尝试使用
- 用户正确/错误使用
- 系统给出纠错
- 复习通过/失败
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class LearningEventType(Enum):
    """学习事件类型。"""

    INTRODUCED = "introduced"          # AI 引入目标词
    ATTEMPTED = "attempted"            # 用户尝试使用目标词
    CORRECT_USAGE = "correct_usage"    # 用户正确使用目标词
    WRONG_USAGE = "wrong_usage"        # 用户错误使用目标词
    CORRECTED = "corrected"            # 系统给出纠错反馈
    REVIEW_PASSED = "review_passed"    # 复习通过
    REVIEW_FAILED = "review_failed"    # 复习失败
    MASTERED = "mastered"              # 判定掌握


@dataclass
class EvaluationResult:
    """一次用户输入的学习评估结果。

    word:        被评估的目标词
    attempted:   用户是否尝试使用该词
    correct:     如果尝试了，是否使用正确
    quality:     0-5 分，给 SM-2 / 掌握度评分使用
    error_type:  错误类型，如 wrong_form / wrong_meaning / grammar
    correction:  推荐改法
    explanation: 简短解释
    """

    word: str
    attempted: bool
    correct: bool
    quality: int
    error_type: Optional[str] = None
    correction: Optional[str] = None
    explanation: Optional[str] = None

    def __post_init__(self):
        self.quality = max(0, min(5, int(self.quality)))
        if not self.attempted:
            self.correct = False


@dataclass
class LearningEvent:
    """单次学习事件记录。"""

    word: str
    event_type: LearningEventType
    quality: Optional[int] = None
    mastery_delta: int = 0
    user_text: str = ""
    ai_feedback: str = ""
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.quality is not None:
            self.quality = max(0, min(5, int(self.quality)))
