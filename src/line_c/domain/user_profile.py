"""用户角色数据类。

每个角色是一个独立的学习档案：自己的英语水平、兴趣标签、生词本和复习队列。
多个角色之间的学习数据完全隔离。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class UserProfile:
    """一个学习角色。

    interests 用字符串列表存储，如 ["ai_tech", "finance", "knowledge"]，
    存入 SQLite 时序列化为 JSON。
    """

    id: int = 0
    name: str = ""
    english_level: str = "middle"  # beginner / primary / middle / high / advanced
    interests: List[str] = field(default_factory=list)
    created_at: str = ""  # ISO 时间戳
