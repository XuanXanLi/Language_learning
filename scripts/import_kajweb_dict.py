#!/usr/bin/env python3
"""从 kajweb/dict 的 JSONL 文件导入 CET-4/CET-6 词汇到 SQLite。

数据源: https://github.com/kajweb/dict (book/ 目录下的 CET4_*.zip / CET6_*.zip)

用法:
    python scripts/import_kajweb_dict.py /tmp/cet_all/       # 从解压目录导入
    python scripts/import_kajweb_dict.py /tmp/cet_all/ --level cet4  # 只导入 CET-4
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from line_c.domain.word import Word
from line_c.engine.vocabulary_repository import VocabularyRepository
from line_c.config import DATABASE_PATH


def _extract_word(entry: dict, level: str) -> dict:
    """从 kajweb/dict 的一行 JSON 中提取字段, 返回扁平 dict。"""
    c = entry["content"]["word"]["content"]

    trans = c.get("trans", [])
    first_trans = trans[0] if trans else {}

    sentence_obj = c.get("sentence", {})
    raw_sentences = sentence_obj.get("sentences", []) if isinstance(sentence_obj, dict) else []

    syno_obj = c.get("syno", {})
    raw_synos = syno_obj.get("synos", []) if isinstance(syno_obj, dict) else []

    phrase_obj = c.get("phrase", {})
    raw_phrases = phrase_obj.get("phrases", []) if isinstance(phrase_obj, dict) else []

    exam = c.get("exam", [])

    return {
        "word": entry["headWord"],
        "phonetic": c.get("ukphone", c.get("usphone", "")),
        "us_phonetic": c.get("usphone", ""),
        "uk_phonetic": c.get("ukphone", ""),
        "us_speech": c.get("usspeech", ""),
        "uk_speech": c.get("ukspeech", ""),
        "part_of_speech": first_trans.get("pos", ""),
        "definition_en": first_trans.get("tranOther", ""),
        "definition_cn": first_trans.get("tranCn", ""),
        "sentences": [
            {"sContent": s["sContent"], "sCn": s["sCn"]}
            for s in raw_sentences if s.get("sContent")
        ],
        "grouped_synonyms": [
            {"pos": s.get("pos", ""), "tran": s.get("tran", ""),
             "hwds": [h["w"] for h in s.get("hwds", []) if h.get("w")]}
            for s in raw_synos
        ],
        "collocations": [
            {"pContent": p["pContent"], "pCn": p["pCn"]}
            for p in raw_phrases if p.get("pContent")
        ],
        "exam_data": json.dumps(exam, ensure_ascii=False) if exam else None,
        "level": level,
        "difficulty": round(min(1.0, max(0.1, len(entry["headWord"]) / 15.0)), 2),
        "topic_tags": [],
        "examples": [],
        "synonyms": [],
        "antonyms": [],
    }


def _parse_jsonl(filepath: Path) -> list[dict]:
    """解析 JSONL 文件（每行一个完整 JSON）, 返回 dict 列表。"""
    entries = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def _merge_entries(all_entries: list[dict]) -> list[dict]:
    """合并同一词在多个文件中的条目, 保留最完整的。

    策略:
    - 取定义最完整的（英释+中释都有）
    - 合并所有不重复的例句
    - 合并所有不重复的短语
    - 合并所有不重复的同义词组
    - 保留有真题数据的那份
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in all_entries:
        groups[e["word"]].append(e)

    merged = []
    for word, entries in groups.items():
        if len(entries) == 1:
            merged.append(entries[0])
            continue

        # 合并: 用定义最完整的为基础
        best = max(entries, key=lambda e: (
            bool(e["definition_en"]) + bool(e["definition_cn"]),
            len(e["sentences"]),
            len(e["collocations"]),
        ))

        # 收集所有例句（去重, 保持顺序）
        seen_sc = set()
        all_sentences = []
        for e in entries:
            for s in e["sentences"]:
                if s["sContent"] not in seen_sc:
                    seen_sc.add(s["sContent"])
                    all_sentences.append(s)
        best["sentences"] = all_sentences

        # 收集所有短语（去重）
        seen_pc = set()
        all_phrases = []
        for e in entries:
            for p in e["collocations"]:
                if p["pContent"] not in seen_pc:
                    seen_pc.add(p["pContent"])
                    all_phrases.append(p)
        best["collocations"] = all_phrases

        # 收集所有同义词组（去重按 pos）
        seen_pos = set()
        all_synos = []
        for e in entries:
            for s in e["grouped_synonyms"]:
                key = (s["pos"], s["tran"])
                if key not in seen_pos:
                    seen_pos.add(key)
                    all_synos.append(s)
        best["grouped_synonyms"] = all_synos

        # 保留有真题数据的那份
        exam_entries = [e for e in entries if e["exam_data"]]
        if exam_entries:
            best["exam_data"] = exam_entries[0]["exam_data"]

        merged.append(best)

    return merged


def import_from_kajweb(jsonl_dir: str, levels: tuple[str, ...] = ("cet4", "cet6")):
    """从解压后的 kajweb/dict JSONL 目录导入词汇。"""
    jsonl_dir = Path(jsonl_dir)

    all_entries = []
    file_map = {
        "cet4": ["CET4_1.json", "CET4_2.json", "CET4_3.json"],
        "cet6": ["CET6_1.json", "CET6_2.json", "CET6_3.json"],
    }

    for level in levels:
        for fname in file_map.get(level, []):
            fpath = jsonl_dir / fname
            if not fpath.exists():
                print(f"Skip missing: {fpath}")
                continue
            entries = _parse_jsonl(fpath)
            print(f"Parsed {len(entries)} words from {fname}")
            for e in entries:
                all_entries.append(_extract_word(e, level))

    print(f"\nTotal raw entries: {len(all_entries)}")
    merged = _merge_entries(all_entries)
    print(f"After dedup merge: {len(merged)} words")

    # 构建 Word 对象并批量导入
    words = []
    for item in merged:
        w = Word(
            word=item["word"],
            phonetic=item["phonetic"],
            us_phonetic=item["us_phonetic"],
            uk_phonetic=item["uk_phonetic"],
            us_speech=item["us_speech"],
            uk_speech=item["uk_speech"],
            part_of_speech=item["part_of_speech"],
            definition_en=item["definition_en"],
            definition_cn=item["definition_cn"],
            examples=item["examples"],
            level=item["level"],
            topic_tags=item["topic_tags"],
            difficulty=item["difficulty"],
            synonyms=item["synonyms"],
            antonyms=item["antonyms"],
            grouped_synonyms=item["grouped_synonyms"],
            exam_data=item["exam_data"],
            sentences=item["sentences"],
            collocations=item["collocations"],
        )
        words.append(w)

    # 导入（先删旧库）
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
        print(f"Removed old database: {DATABASE_PATH}")

    repo = VocabularyRepository(DATABASE_PATH)
    repo.add_words(words)
    total = repo.word_count()
    repo.close()

    # 统计
    cet4_count = sum(1 for m in merged if m["level"] == "cet4")
    cet6_count = sum(1 for m in merged if m["level"] == "cet6")
    print(f"\n=== Import Complete ===")
    print(f"CET-4: {cet4_count} words")
    print(f"CET-6: {cet6_count} words")
    print(f"Total: {total} words in {DATABASE_PATH}")
    print(f"DB size: {DATABASE_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_kajweb_dict.py <jsonl_dir> [--level cet4|cet6]")
        print("Example: python scripts/import_kajweb_dict.py /tmp/cet_all/")
        sys.exit(1)

    jsonl_dir = sys.argv[1]
    levels = ("cet4", "cet6")

    if "--level" in sys.argv:
        idx = sys.argv.index("--level")
        if idx + 1 < len(sys.argv):
            levels = (sys.argv[idx + 1],)

    import_from_kajweb(jsonl_dir, levels)
