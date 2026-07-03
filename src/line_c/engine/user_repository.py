"""用户角色仓库。

管理 user_profile 表的 CRUD 操作。
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from ..domain.user_profile import UserProfile


class UserRepository:
    """管理 user_profile 表。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                english_level TEXT NOT NULL DEFAULT 'middle',
                interests TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    # ── 增 ──

    def create(self, profile: UserProfile) -> int:
        """创建角色，返回新 ID。"""
        cursor = self._conn.execute(
            "INSERT INTO user_profile (name, english_level, interests) VALUES (?, ?, ?)",
            (profile.name, profile.english_level, json.dumps(profile.interests, ensure_ascii=False)),
        )
        self._conn.commit()
        return cursor.lastrowid

    # ── 查 ──

    def get_by_id(self, user_id: int) -> Optional[UserProfile]:
        """按 ID 查单个角色。"""
        row = self._conn.execute(
            "SELECT * FROM user_profile WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    def get_all(self) -> List[UserProfile]:
        """获取所有角色列表。"""
        rows = self._conn.execute(
            "SELECT * FROM user_profile ORDER BY created_at"
        ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def count(self) -> int:
        """角色总数。"""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM user_profile").fetchone()
        return row["cnt"]

    # ── 改 ──

    def update(self, profile: UserProfile) -> bool:
        """更新角色信息。返回是否成功。"""
        cursor = self._conn.execute(
            "UPDATE user_profile SET name = ?, english_level = ?, interests = ? WHERE id = ?",
            (profile.name, profile.english_level, json.dumps(profile.interests, ensure_ascii=False), profile.id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── 删 ──

    def delete(self, user_id: int) -> bool:
        """删除角色。级联删除关联的会话和生词（通过外键 ON DELETE CASCADE）。"""
        cursor = self._conn.execute(
            "DELETE FROM user_profile WHERE id = ?", (user_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── 工具 ──

    def _row_to_profile(self, row: sqlite3.Row) -> UserProfile:
        interests = json.loads(row["interests"]) if row["interests"] else []
        return UserProfile(
            id=row["id"],
            name=row["name"],
            english_level=row["english_level"],
            interests=interests,
            created_at=row["created_at"] or "",
        )

    def close(self):
        self._conn.close()
