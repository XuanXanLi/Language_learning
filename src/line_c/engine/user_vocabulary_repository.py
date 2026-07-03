"""用户生词仓库。

管理 user_vocabulary 表的 CRUD 操作。
核心功能：点击取词保存、复习队列查询、SM-2 字段更新、掌握判定。
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from ..domain.user_vocabulary import UserVocabulary, VocabState


class UserVocabularyRepository:
    """管理 user_vocabulary 表。

    每个角色对每个词只有一条记录（user_id + word 唯一约束）。
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS user_vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                session_id INTEGER,
                lookup_count INTEGER NOT NULL DEFAULT 1,
                state TEXT NOT NULL DEFAULT 'NEW',
                mastery_score INTEGER NOT NULL DEFAULT 0,
                consecutive_correct INTEGER NOT NULL DEFAULT 0,
                repetition INTEGER NOT NULL DEFAULT 0,
                interval_days REAL NOT NULL DEFAULT 0.0,
                ef REAL NOT NULL DEFAULT 2.5,
                next_review_at TIMESTAMP,
                last_reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, word)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_uv_user_state ON user_vocabulary(user_id, state)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_uv_review ON user_vocabulary(user_id, next_review_at)
        """)
        self._conn.commit()

    # ── 点击取词（upsert）──

    def upsert_lookup(
        self,
        word: str,
        user_id: int,
        session_id: Optional[int] = None,
    ) -> bool:
        """记录一次查词点击。

        如果这个词该角色已经查过 → lookup_count +1。
        如果第一次查 → 创建新记录（状态 NEW）。

        返回 True 表示是新词，False 表示已有记录（仅 +count）。
        """
        existing = self._conn.execute(
            "SELECT id, lookup_count FROM user_vocabulary WHERE user_id = ? AND word = ?",
            (user_id, word),
        ).fetchone()

        if existing:
            self._conn.execute(
                "UPDATE user_vocabulary SET lookup_count = ? WHERE id = ?",
                (existing["lookup_count"] + 1, existing["id"]),
            )
            self._conn.commit()
            return False

        now = datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO user_vocabulary
               (user_id, word, session_id, state, next_review_at, created_at)
               VALUES (?, ?, ?, 'NEW', ?, ?)""",
            (user_id, word, session_id, now, now),
        )
        self._conn.commit()
        return True

    # ── 复习队列 ──

    def get_review_queue(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取到期待复习的词。

        条件：state IN ('NEW', 'LEARNING') 且 next_review_at <= now。
        NEW 词第一次进入复习时 next_review_at 在 upsert 时已设为 created_at。
        """
        now = datetime.now().isoformat()
        rows = self._conn.execute(
            """SELECT * FROM user_vocabulary
               WHERE user_id = ? AND state IN ('NEW', 'LEARNING')
               AND next_review_at <= ?
               ORDER BY next_review_at ASC
               LIMIT ?""",
            (user_id, now, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_spot_check_words(self, user_id: int, max_count: int = 1) -> List[Dict]:
        """随机抽查已掌握词。

        MASTERED 且 last_reviewed_at 距今 >= 30 天。
        """
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        rows = self._conn.execute(
            """SELECT * FROM user_vocabulary
               WHERE user_id = ? AND state = 'MASTERED'
               AND (last_reviewed_at IS NULL OR last_reviewed_at <= ?)
               ORDER BY RANDOM()
               LIMIT ?""",
            (user_id, cutoff, max_count),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_review_queue_count(self, user_id: int) -> int:
        """到期待复习词的总数（不限 20）。"""
        now = datetime.now().isoformat()
        row = self._conn.execute(
            """SELECT COUNT(*) as cnt FROM user_vocabulary
               WHERE user_id = ? AND state IN ('NEW', 'LEARNING')
               AND next_review_at <= ?""",
            (user_id, now),
        ).fetchone()
        return row["cnt"] if row else 0

    # ── SM-2 更新 ──

    def update_review(
        self,
        word: str,
        user_id: int,
        state: str,
        repetition: int,
        interval_days: float,
        ef: float,
        consecutive_correct: int,
        next_review_at: str,
    ) -> bool:
        """复习后更新 SM-2 字段。"""
        now = datetime.now().isoformat()
        cursor = self._conn.execute(
            """UPDATE user_vocabulary SET
               state = ?, repetition = ?, interval_days = ?, ef = ?,
               consecutive_correct = ?, next_review_at = ?,
               last_reviewed_at = ?
               WHERE user_id = ? AND word = ?""",
            (state, repetition, interval_days, ef,
             consecutive_correct, next_review_at,
             now, user_id, word),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── 查 ──

    def get_by_user(self, user_id: int) -> List[Dict]:
        """获取一个角色的所有生词。"""
        rows = self._conn.execute(
            "SELECT * FROM user_vocabulary WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_session(self, session_id: int) -> List[Dict]:
        """获取某个会话中收集的生词。"""
        rows = self._conn.execute(
            "SELECT * FROM user_vocabulary WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_word(self, word: str, user_id: int) -> Optional[Dict]:
        """查角色对某个词的掌握记录。"""
        row = self._conn.execute(
            "SELECT * FROM user_vocabulary WHERE user_id = ? AND word = ?",
            (user_id, word),
        ).fetchone()
        return dict(row) if row else None

    def get_mastered_count(self, user_id: int) -> int:
        """已掌握词数。"""
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM user_vocabulary WHERE user_id = ? AND state = 'MASTERED'",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    def get_total_count(self, user_id: int) -> int:
        """该角色生词总数。"""
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM user_vocabulary WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0

    def close(self):
        self._conn.close()
