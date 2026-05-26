from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Word:
    """一个英语词汇的全部信息。"""
    word: str
    phonetic: str                    # 默认显示音标（优先英音）
    part_of_speech: str
    definition_en: str
    definition_cn: str
    examples: List[str] = field(default_factory=list)
    level: str = "cet4"
    topic_tags: List[str] = field(default_factory=list)
    difficulty: float = 0.5
    synonyms: List[str] = field(default_factory=list)
    antonyms: List[str] = field(default_factory=list)
    # kajweb/dict 扩展字段
    us_phonetic: str = ""
    uk_phonetic: str = ""
    us_speech: str = ""              # 有道 API 参数: "word&type=2"
    uk_speech: str = ""              # 有道 API 参数: "word&type=1"
    exam_data: Optional[str] = None  # 真题 JSON
    sentences: List[dict] = field(default_factory=list)    # [{sContent, sCn}]
    collocations: List[dict] = field(default_factory=list)  # [{pContent, pCn}]
    grouped_synonyms: List[dict] = field(default_factory=list)  # [{pos, tran, hwds}]
