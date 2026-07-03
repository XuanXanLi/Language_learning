"""对话会话仓库。

管理 chat_session 表的 CRUD 操作。
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..domain.chat_session import ChatSession


class ChatSessionRepository:
    """管理 chat_session 表。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_session (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_title TEXT NOT NULL,
                topic_source TEXT NOT NULL DEFAULT 'llm',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP
            )
        """)
        self._conn.commit()

    # ── 增 ──

    def create(self, session: ChatSession) -> int:
        """创建新会话，返回 ID。"""
        cursor = self._conn.execute(
            "INSERT INTO chat_session (user_id, topic_title, topic_source) VALUES (?, ?, ?)",
            (session.user_id, session.topic_title, session.topic_source),
        )
        self._conn.commit()
        return cursor.lastrowid

    # ── 查 ──

    def get_by_id(self, session_id: int) -> Optional[ChatSession]:
        """按 ID 查会话。"""
        row = self._conn.execute(
            "SELECT * FROM chat_session WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def get_by_user(self, user_id: int, limit: int = 20) -> List[ChatSession]:
        """获取一个角色的最近会话列表。"""
        rows = self._conn.execute(
            "SELECT * FROM chat_session WHERE user_id = ? ORDER BY started_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    # ── 改 ──

    def end_session(self, session_id: int) -> bool:
        """结束会话，写入 ended_at 时间戳。"""
        now = datetime.now().isoformat()
        cursor = self._conn.execute(
            "UPDATE chat_session SET ended_at = ? WHERE id = ?",
            (now, session_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── 工具 ──

    def _row_to_session(self, row: sqlite3.Row) -> ChatSession:
        return ChatSession(
            id=row["id"],
            user_id=row["user_id"],
            topic_title=row["topic_title"],
            topic_source=row["topic_source"],
            started_at=row["started_at"] or "",
            ended_at=row["ended_at"],
        )

    def close(self):
        self._conn.close()
