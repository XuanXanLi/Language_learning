from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .vocabulary_state import VocabularyState


@dataclass
class LearningRecord:
    """单次学习事件记录。

    每次用户在对话中遇到或使用一个词，系统记一条记录。
    这些记录用于追踪学习轨迹和分析薄弱点。
    """
    word: str                              # 哪个词
    from_state: VocabularyState            # 迁移前状态
    to_state: VocabularyState              # 迁移后状态
    timestamp: datetime = field(default_factory=datetime.now)  # 记录时间
    session_id: Optional[str] = None       # 发生在哪个对话会话
    quality: Optional[int] = None          # 用户表现质量 0-5（仅复习时用）
