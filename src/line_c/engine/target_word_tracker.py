"""目标词追踪器。

职责：
- 记录本轮中文焦点词
- 从助手回复的“翻译/复述”部分提取候选英文目标词
- 维护当前活跃目标词集合

这一层尽量保持轻量，不直接依赖 UI。
"""

import re
from typing import Iterable, List, Set


_TRACKER_STOP_WORDS = {
    "you", "can", "say", "use", "using", "the", "and", "or", "but",
    "this", "that", "here", "there", "with", "from", "into", "about",
    "your", "partner", "mean", "means", "word", "english", "sentence",
}


class TargetWordTracker:
    """追踪当前会话的目标词。"""

    def __init__(self):
        self._current_focus: List[str] = []
        self._active_targets: List[str] = []
        self._all_targets: Set[str] = set()

    def reset(self):
        self._current_focus = []
        self._active_targets = []
        self._all_targets = set()

    def set_focus(self, chinese_words: Iterable[str]):
        """更新当前中文焦点词。"""
        self._current_focus = [w for w in chinese_words if w]

    def ingest_assistant_response(self, text: str, limit: int = 3) -> List[str]:
        """从助手回复里提取候选目标词。

        只取第一句，优先抓“先复述再回答”里的翻译词，避免把整段回复里
        所有 CET 词都当成目标词。
        """
        lead_text = self._extract_lead_sentence(text)
        words = self._extract_words(lead_text)
        candidates = []
        for word in words:
            if word in _TRACKER_STOP_WORDS:
                continue
            if word not in candidates:
                candidates.append(word)
            if len(candidates) >= limit:
                break

        self._active_targets = candidates
        self._all_targets.update(candidates)
        return list(candidates)

    def get_active_targets(self) -> List[str]:
        return list(self._active_targets)

    def get_current_target(self) -> str | None:
        """返回当前最重要的一个目标词。

        自由聊天模式下默认只围绕一个词轻量评估，避免一次弹出多条纠错。
        """
        return self._active_targets[0] if self._active_targets else None

    def get_all_targets(self) -> List[str]:
        return sorted(self._all_targets)

    def has_active_targets(self) -> bool:
        return bool(self._active_targets)

    @staticmethod
    def _extract_lead_sentence(text: str) -> str:
        parts = re.split(r"[.!?。！？\n]", text, maxsplit=1)
        return parts[0] if parts else text

    @staticmethod
    def _extract_words(text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z'\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 2]
