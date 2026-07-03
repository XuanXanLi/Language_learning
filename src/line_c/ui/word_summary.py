"""词汇追踪面板。

药丸标签分类展示当前会话中的词汇：
- 紫色 = 目标词（AI 翻译引入的英文词）
- 绿色 = 你用过的
- 蓝色 = 复习中
"""

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class _PillTag(QLabel):
    """彩色药丸标签。"""

    COLORS = {
        "purple": ("#7C3AED", "white"),
        "green":  ("#22C55E", "white"),
        "blue":   ("#3B82F6", "white"),
    }

    def __init__(self, text: str, color: str, parent=None):
        super().__init__(text, parent)
        bg, fg = self.COLORS.get(color, ("#6B7280", "white"))
        f = QFont(); f.setPixelSize(11); f.setBold(True); self.setFont(f)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)
        self.setMinimumWidth(52)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 11px;
                padding: 2px 10px;
            }}
        """)


class _VocabCard(QWidget):
    """单张词汇卡片：左侧词汇，右侧药丸标签。"""

    def __init__(self, word: str, meaning: str, tag_text: str, tag_color: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 左侧文字
        left = QVBoxLayout()
        left.setSpacing(1)
        word_label = QLabel(word)
        f = QFont(); f.setPixelSize(13); f.setBold(True); word_label.setFont(f)
        word_label.setStyleSheet("color: #1F2937; background: transparent;")
        left.addWidget(word_label)

        if meaning:
            meaning_label = QLabel(meaning)
            f = QFont(); f.setPixelSize(10); meaning_label.setFont(f)
            meaning_label.setStyleSheet("color: #6B7280; background: transparent;")
            left.addWidget(meaning_label)

        layout.addLayout(left)
        layout.addStretch()

        tag = _PillTag(tag_text, tag_color)
        layout.addWidget(tag)

        self.setStyleSheet("""
            _VocabCard {
                background: white;
                border-radius: 12px;
                border: 1px solid rgba(124, 58, 237, 12);
            }
        """)


class WordSummary(QWidget):
    """词汇追踪面板。

    用法：
        summary = WordSummary()
        manager.word_event.connect(summary.on_word_event)
    """

    PRIORITY = {
        "target": 1,
        "used": 2,
        "learning": 3,
    }
    TAGS = {
        "target": ("目标词", "purple"),
        "used": ("你用过", "green"),
        "learning": ("复习中", "blue"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self._words: dict = {}

        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel("  词汇追踪")
        f = QFont(); f.setPixelSize(15); f.setBold(True); title.setFont(f)
        title.setStyleSheet("color: #4C1D95; padding: 14px 0 10px 0; background: transparent;")
        layout.addWidget(title)

        # 可滚动内容区
        self.content_layout = QVBoxLayout()
        self.content_layout.setAlignment(Qt.AlignTop)
        self.content_layout.setSpacing(8)

        content_widget = QWidget()
        content_widget.setLayout(self.content_layout)
        content_widget.setStyleSheet("background: transparent;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_widget)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll, stretch=1)

        self._rebuild()

    def on_word_event(self, word: str, event: str, state: str):
        """处理 word_event 信号。

        event: "target" | "used" | "learning"
        """
        if event not in self.PRIORITY:
            return

        existing = self._words.get(word)
        if existing is None or self.PRIORITY[event] >= self.PRIORITY[existing["event"]]:
            self._words[word] = {"event": event, "state": state}

        self._rebuild()

    def reset(self):
        self._words.clear()
        self._rebuild()

    def _rebuild(self):
        # 清空
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        if not self._words:
            empty = QLabel("等待对话开始...\n用中文问词，或用英文聊天，\n词汇会自动出现在这里")
            f = QFont(); f.setPixelSize(11); empty.setFont(f)
            empty.setStyleSheet("color: #9CA3AF; padding: 20px; background: transparent;")
            empty.setAlignment(Qt.AlignCenter)
            empty.setWordWrap(True)
            self.content_layout.addWidget(empty)
            return

        ordered = sorted(
            self._words.items(),
            key=lambda item: self.PRIORITY[item[1]["event"]],
        )
        for word, info in ordered:
            tag_text, color = self.TAGS[info["event"]]
            card = _VocabCard(word, "", tag_text, color)
            self.content_layout.addWidget(card)

        self.content_layout.addStretch()
