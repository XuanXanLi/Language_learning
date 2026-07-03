"""词汇数据仓库（Repository）。

Repository（仓库模式）的含义：把所有 SQL 操作集中在一个类里，
外部代码不直接写 SQL，而是调用 Repository 的方法。
这样做的好处是：如果以后换数据库（比如从 SQLite 换成 MySQL），
只需要改这一个文件。
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from ..domain.word import Word
from ..domain.vocabulary_state import VocabularyState


class VocabularyRepository:
    """管理词汇数据的 SQLite 仓库。

    SQLite 是 Python 内置的轻量数据库，所有数据存在一个 .db 文件里。
    不需要安装数据库服务器，非常适合嵌入式项目。
    """

    def __init__(self, db_path: Path):
        """初始化仓库。

        参数说明：
        db_path: SQLite 数据库文件的路径（可以是还不存在的文件，
                 第一次连接时会自动创建）
        """
        self.db_path = db_path
        # 确保父目录存在（如 data/db/）
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # 建立连接
        self._conn = sqlite3.connect(str(db_path))
        # row_factory：让查询结果可以用列名访问，如 row["word"] 而不是 row[0]
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self._conn.execute("""
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY,
                phonetic TEXT NOT NULL,
                us_phonetic TEXT NOT NULL DEFAULT '',
                uk_phonetic TEXT NOT NULL DEFAULT '',
                us_speech TEXT NOT NULL DEFAULT '',
                uk_speech TEXT NOT NULL DEFAULT '',
                part_of_speech TEXT NOT NULL,
                definition_en TEXT NOT NULL,
                definition_cn TEXT NOT NULL,
                examples TEXT NOT NULL DEFAULT '[]',
                level TEXT NOT NULL DEFAULT 'cet4',
                topic_tags TEXT NOT NULL DEFAULT '[]',
                difficulty REAL NOT NULL DEFAULT 0.5,
                synonyms TEXT NOT NULL DEFAULT '[]',
                antonyms TEXT NOT NULL DEFAULT '[]',
                grouped_synonyms TEXT NOT NULL DEFAULT '[]',
                exam_data TEXT,
                state TEXT NOT NULL DEFAULT 'UNKNOWN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_words_state ON words(state)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_words_level ON words(level)
        """)
        # 例句子表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS word_sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                s_content TEXT NOT NULL,
                s_cn TEXT NOT NULL,
                idx INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (word) REFERENCES words(word)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentences_word ON word_sentences(word)
        """)
        # 短语搭配子表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS word_collocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                p_content TEXT NOT NULL,
                p_cn TEXT NOT NULL,
                FOREIGN KEY (word) REFERENCES words(word)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_collocations_word ON word_collocations(word)
        """)
        # 学习掌握度表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS word_mastery (
                word TEXT PRIMARY KEY,
                mastery_score INTEGER NOT NULL DEFAULT 0,
                seen_count INTEGER NOT NULL DEFAULT 0,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                wrong_count INTEGER NOT NULL DEFAULT 0,
                last_seen_at TIMESTAMP,
                last_attempted_at TIMESTAMP,
                last_quality INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word) REFERENCES words(word)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                event_type TEXT NOT NULL,
                quality INTEGER,
                mastery_delta INTEGER NOT NULL DEFAULT 0,
                user_text TEXT NOT NULL DEFAULT '',
                ai_feedback TEXT NOT NULL DEFAULT '',
                error_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (word) REFERENCES words(word)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_events_word ON learning_events(word)
        """)
        self._conn.commit()

    # ── 增 ──

    def add_word(self, word: Word):
        self._conn.execute("""
            INSERT OR REPLACE INTO words
                (word, phonetic, us_phonetic, uk_phonetic, us_speech, uk_speech,
                 part_of_speech, definition_en, definition_cn,
                 examples, level, topic_tags, difficulty, synonyms, antonyms,
                 grouped_synonyms, exam_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            word.word, word.phonetic,
            word.us_phonetic, word.uk_phonetic, word.us_speech, word.uk_speech,
            word.part_of_speech, word.definition_en, word.definition_cn,
            json.dumps(word.examples, ensure_ascii=False),
            word.level,
            json.dumps(word.topic_tags, ensure_ascii=False),
            word.difficulty,
            json.dumps(word.synonyms, ensure_ascii=False),
            json.dumps(word.antonyms, ensure_ascii=False),
            json.dumps(word.grouped_synonyms, ensure_ascii=False),
            word.exam_data,
        ))
        self._conn.commit()
        self._save_word_children(word)

    def add_words(self, words: List[Word]):
        """批量添加单词。一次性提交，比循环 add_word 快很多。"""
        data = [(
            w.word, w.phonetic,
            w.us_phonetic, w.uk_phonetic, w.us_speech, w.uk_speech,
            w.part_of_speech, w.definition_en, w.definition_cn,
            json.dumps(w.examples, ensure_ascii=False),
            w.level,
            json.dumps(w.topic_tags, ensure_ascii=False),
            w.difficulty,
            json.dumps(w.synonyms, ensure_ascii=False),
            json.dumps(w.antonyms, ensure_ascii=False),
            json.dumps(w.grouped_synonyms, ensure_ascii=False),
            w.exam_data,
        ) for w in words]
        self._conn.executemany("""
            INSERT OR REPLACE INTO words
                (word, phonetic, us_phonetic, uk_phonetic, us_speech, uk_speech,
                 part_of_speech, definition_en, definition_cn,
                 examples, level, topic_tags, difficulty, synonyms, antonyms,
                 grouped_synonyms, exam_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self._conn.commit()
        for w in words:
            self._save_word_children(w)

    def record_learning_event(
        self,
        word: str,
        event_type: str,
        quality: Optional[int] = None,
        mastery_delta: int = 0,
        user_text: str = "",
        ai_feedback: str = "",
        error_type: Optional[str] = None,
    ):
        """记录一次学习事件。"""
        self._conn.execute("""
            INSERT INTO learning_events
                (word, event_type, quality, mastery_delta, user_text, ai_feedback, error_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (word, event_type, quality, mastery_delta, user_text, ai_feedback, error_type))
        self._conn.commit()

    def get_word_mastery(self, word: str) -> Optional[dict]:
        """获取一个词的掌握度信息。"""
        row = self._conn.execute(
            "SELECT * FROM word_mastery WHERE word = ?", (word,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def update_word_mastery(
        self,
        word: str,
        mastery_score: int,
        seen_count: Optional[int] = None,
        attempt_count: Optional[int] = None,
        correct_count: Optional[int] = None,
        wrong_count: Optional[int] = None,
        last_seen_at: Optional[str] = None,
        last_attempted_at: Optional[str] = None,
        last_quality: Optional[int] = None,
    ) -> None:
        """新增或更新一个词的掌握度记录。"""
        existing = self.get_word_mastery(word) or {}
        payload = {
            "word": word,
            "mastery_score": mastery_score,
            "seen_count": seen_count if seen_count is not None else existing.get("seen_count", 0),
            "attempt_count": attempt_count if attempt_count is not None else existing.get("attempt_count", 0),
            "correct_count": correct_count if correct_count is not None else existing.get("correct_count", 0),
            "wrong_count": wrong_count if wrong_count is not None else existing.get("wrong_count", 0),
            "last_seen_at": last_seen_at if last_seen_at is not None else existing.get("last_seen_at"),
            "last_attempted_at": last_attempted_at if last_attempted_at is not None else existing.get("last_attempted_at"),
            "last_quality": last_quality if last_quality is not None else existing.get("last_quality"),
        }
        self._conn.execute("""
            INSERT OR REPLACE INTO word_mastery
                (word, mastery_score, seen_count, attempt_count, correct_count, wrong_count,
                 last_seen_at, last_attempted_at, last_quality, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            payload["word"],
            payload["mastery_score"],
            payload["seen_count"],
            payload["attempt_count"],
            payload["correct_count"],
            payload["wrong_count"],
            payload["last_seen_at"],
            payload["last_attempted_at"],
            payload["last_quality"],
        ))
        self._conn.commit()

    def get_weak_words(self, limit: int = 20) -> List[str]:
        """返回掌握度最低的一批词。"""
        rows = self._conn.execute(
            "SELECT word FROM word_mastery ORDER BY mastery_score ASC, updated_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [row["word"] for row in rows]

    # ── 查 ──

    def get_word(self, word: str) -> Optional[Word]:
        """按拼写查询单个词。找不到返回 None。"""
        row = self._conn.execute(
            "SELECT * FROM words WHERE word = ?", (word,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_word(row)

    def get_words_by_level(self, level: str, limit: int = 100) -> List[Word]:
        """按等级筛选词汇（cet4 / cet6 / custom）。"""
        rows = self._conn.execute(
            "SELECT * FROM words WHERE level = ? LIMIT ?", (level, limit)
        ).fetchall()
        return [self._row_to_word(r) for r in rows]

    def get_words_by_topic(self, topic: str, limit: int = 20) -> List[Word]:
        """按话题标签搜索。

        LIKE 是 SQL 的模糊匹配，% 是通配符。
        例如 topic_tags 存的是 ["travel","daily"]，
        LIKE '%"travel"%' 就能匹配到。
        """
        rows = self._conn.execute(
            "SELECT * FROM words WHERE topic_tags LIKE ? LIMIT ?",
            (f'%"{topic}"%', limit)
        ).fetchall()
        return [self._row_to_word(r) for r in rows]

    def get_words_by_state(
        self, state: VocabularyState, limit: int = 50
    ) -> List[Word]:
        """按学习状态筛选。"""
        rows = self._conn.execute(
            "SELECT * FROM words WHERE state = ? LIMIT ?",
            (state.name, limit)
        ).fetchall()
        return [self._row_to_word(r) for r in rows]

    def word_count(self) -> int:
        """返回词库总词数。"""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM words").fetchone()
        return row["cnt"]

    # ── 改 ──

    def update_word_state(
        self, word: str, new_state: VocabularyState
    ) -> bool:
        """更新一个词的学习状态。返回是否成功（True = 更新了数据）。"""
        cursor = self._conn.execute(
            "UPDATE words SET state = ? WHERE word = ?",
            (new_state.name, word)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    # ── 工具 ──

    def _row_to_word(self, row: sqlite3.Row) -> Word:
        """把数据库的一行记录转换为 Word 对象。"""
        examples = json.loads(row["examples"]) if row["examples"] else []
        topic_tags = json.loads(row["topic_tags"]) if row["topic_tags"] else []
        synonyms = json.loads(row["synonyms"]) if row["synonyms"] else []
        antonyms = json.loads(row["antonyms"]) if row["antonyms"] else []
        grouped_synonyms = json.loads(row["grouped_synonyms"]) if row["grouped_synonyms"] else []
        sentences = self._load_sentences(row["word"])
        collocations = self._load_collocations(row["word"])

        return Word(
            word=row["word"],
            phonetic=row["phonetic"],
            us_phonetic=row["us_phonetic"] if "us_phonetic" in row.keys() else "",
            uk_phonetic=row["uk_phonetic"] if "uk_phonetic" in row.keys() else "",
            us_speech=row["us_speech"] if "us_speech" in row.keys() else "",
            uk_speech=row["uk_speech"] if "uk_speech" in row.keys() else "",
            part_of_speech=row["part_of_speech"],
            definition_en=row["definition_en"],
            definition_cn=row["definition_cn"],
            examples=examples,
            level=row["level"],
            topic_tags=topic_tags,
            difficulty=row["difficulty"],
            synonyms=synonyms,
            antonyms=antonyms,
            grouped_synonyms=grouped_synonyms,
            exam_data=row["exam_data"] if "exam_data" in row.keys() else None,
            sentences=sentences,
            collocations=collocations,
        )

    def _save_word_children(self, word: Word):
        """保存例句和短语到子表。"""
        # 例句
        self._conn.execute("DELETE FROM word_sentences WHERE word = ?", (word.word,))
        for i, s in enumerate(word.sentences):
            self._conn.execute(
                "INSERT INTO word_sentences (word, s_content, s_cn, idx) VALUES (?, ?, ?, ?)",
                (word.word, s["sContent"], s["sCn"], i),
            )
        # 短语
        self._conn.execute("DELETE FROM word_collocations WHERE word = ?", (word.word,))
        for c in word.collocations:
            self._conn.execute(
                "INSERT INTO word_collocations (word, p_content, p_cn) VALUES (?, ?, ?)",
                (word.word, c["pContent"], c["pCn"]),
            )
        self._conn.commit()

    def _load_sentences(self, word: str) -> List[dict]:
        rows = self._conn.execute(
            "SELECT s_content, s_cn FROM word_sentences WHERE word = ? ORDER BY idx",
            (word,),
        ).fetchall()
        return [{"sContent": r["s_content"], "sCn": r["s_cn"]} for r in rows]

    def _load_collocations(self, word: str) -> List[dict]:
        rows = self._conn.execute(
            "SELECT p_content, p_cn FROM word_collocations WHERE word = ?",
            (word,),
        ).fetchall()
        return [{"pContent": r["p_content"], "pCn": r["p_cn"]} for r in rows]

    def close(self):
        """关闭数据库连接。应用退出前调用。"""
        self._conn.close()
