"""对话会话数据类。

每次从 Page 2 进入 Page 3 开始一个新会话。
同一个话题可以开多个会话（每次都是新的对话）。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ChatSession:
    """一次对话会话的记录。

    包含话题信息、时间戳，用于关联该会话中收集的生词。
    """

    id: int = 0
    user_id: int = 0
    topic_title: str = ""           # 话题标题（来自LLM生成或用户输入）
    topic_source: str = "llm"       # "llm" / "user" / "fallback" / "rss"
    started_at: str = ""            # ISO 时间戳
    ended_at: Optional[str] = None  # 退出聊天时写入
