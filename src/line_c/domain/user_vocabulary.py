"""用户生词数据类。

每个角色有独立的生词本。词从对话中点击取词而来，
之后进入 SM-2 间隔复习队列。掌握判定后进入抽查池。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class VocabState(Enum):
    """用户生词学习阶段。

    比旧五阶段状态机简化，只关注"这个词我掌握了吗"：
    - NEW: 刚点击查过词，还没进入复习队列
    - LEARNING: 已进入 SM-2 复习队列
    - MASTERED: 连续正确 + 足够间隔 → 判定掌握
    """

    NEW = "NEW"
    LEARNING = "LEARNING"
    MASTERED = "MASTERED"


@dataclass
class UserVocabulary:
    """一个角色对一个词的掌握记录。

    同一个角色不会重复记录同一个词（user_id + word 唯一约束）。
    点击同一个词多次 → lookup_count 递增，不创建新记录。
    """

    id: int = 0
    user_id: int = 0
    word: str = ""
    session_id: Optional[int] = None  # 首次遇到该词的会话 ID
    lookup_count: int = 1             # 被点击查词次数
    state: str = "NEW"                # VocabState 的值

    # 掌握度
    mastery_score: int = 0            # 0-100 掌握度评分

    # SM-2 状态（持久化到 DB）
    consecutive_correct: int = 0      # 连续正确次数
    repetition: int = 0               # SM-2 repetition
    interval_days: float = 0.0        # SM-2 interval
    ef: float = 2.5                   # SM-2 easiness factor

    # 时间
    next_review_at: Optional[str] = None    # ISO 时间戳
    last_reviewed_at: Optional[str] = None  # ISO 时间戳
    created_at: str = ""                    # ISO 时间戳
