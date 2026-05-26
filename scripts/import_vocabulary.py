#!/usr/bin/env python3
"""将 JSON 词汇文件导入 SQLite 数据库。

用法：
    python scripts/import_vocabulary.py                     # 导入默认的 cet4_seed.json
    python scripts/import_vocabulary.py data/vocab/my.json  # 导入自定义 JSON
"""

import json
import sys
from pathlib import Path

# 把项目根目录加到 Python 的模块搜索路径（sys.path）里，
# 这样脚本在任何位置执行都能 import 到 src.line_c.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from line_c.domain.word import Word
from line_c.engine.vocabulary_repository import VocabularyRepository
from line_c.config import DATABASE_PATH


def import_json_to_db(json_path: Path, db_path: Path) -> int:
    """读取 JSON 文件，将词条导入数据库。返回导入数量。"""
    if not json_path.exists():
        print(f"Error: File not found → {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        raw_list = json.load(f)

    # JSON 里的列表字段可能是字符串（json.dumps后二次序列化），
    # 也可能是直接的 Python 列表，兼容两种情况
    words = []
    for item in raw_list:
        word = Word(
            word=item["word"],
            phonetic=item.get("phonetic", ""),
            part_of_speech=item.get("pos", item.get("part_of_speech", "")),
            definition_en=item.get("def_en", item.get("definition_en", "")),
            definition_cn=item.get("def_cn", item.get("definition_cn", "")),
            examples=_as_list(item.get("examples", [])),
            level=item.get("level", "cet4"),
            topic_tags=_as_list(item.get("topic_tags", [])),
            difficulty=float(item.get("difficulty", 0.5)),
            synonyms=_as_list(item.get("synonyms", [])),
            antonyms=_as_list(item.get("antonyms", [])),
        )
        words.append(word)

    repo = VocabularyRepository(db_path)
    repo.add_words(words)
    total = repo.word_count()
    repo.close()

    print(f"Imported {len(words)} words → {db_path} (total: {total})")
    return len(words)


def _as_list(value):
    """确保值是 Python 列表。

    处理两种输入情况：
    1. value 已经是 list → 直接返回
    2. value 是 JSON 字符串 → 解析为 list
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return []


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    else:
        input_path = PROJECT_ROOT / "data" / "vocab" / "cet4_seed.json"

    import_json_to_db(input_path, DATABASE_PATH)
