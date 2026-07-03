"""聊天页 — 两栏布局 + 点击取词。

左：对话气泡区（QLabel 自适应尺寸 + 点击取词）+ 输入框
右：本次会话生词面板
"""

import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QFontMetrics

from ..widgets.word_popup import WordPopup

# ── 停用词（点击这些词不弹出释义）──
STOP_WORDS = {
    "the", "a", "an", "is", "am", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "can", "could", "may", "might", "must", "to", "for", "of",
    "in", "on", "at", "by", "with", "from", "up", "down", "out", "off",
    "and", "or", "but", "if", "because", "as", "while", "not", "no",
    "so", "than", "too", "very", "just", "also", "now", "then", "here",
    "there", "when", "where", "why", "how", "all", "both", "each", "few",
    "more", "most", "other", "some", "such", "only", "own", "same",
    "i", "me", "my", "you", "your", "he", "him", "his", "she", "her",
    "it", "its", "we", "us", "our", "they", "them", "their",
    "this", "that", "these", "those", "yes", "yeah", "nope",
    "hi", "hey", "hello", "oh", "ok", "okay", "please", "thanks",
    "don", "didn", "doesn", "won", "wouldn", "can", "couldn",
    "isn", "aren", "wasn", "weren", "haven", "hasn", "hadn",
}


class _TappableBubble(QLabel):
    """可点击取词的聊天气泡 — 基于 QLabel，尺寸天然正确。"""

    word_clicked = pyqtSignal(str)

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setText(text)
        self.setTextFormat(Qt.RichText)  # 支持 <b> <br> 等 HTML
        self.setMaximumWidth(520)
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)

        f = QFont(); f.setPixelSize(14); self.setFont(f)

        if is_user:
            self.setStyleSheet("""
                QLabel {
                    background: #DCFCE7; color: #14532D;
                    border: 1px solid #BBF7D0;
                    border-radius: 12px; border-top-right-radius: 4px;
                    padding: 10px 14px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background: white; color: #1F2937;
                    border: 1px solid #E5E7EB;
                    border-radius: 12px; border-top-left-radius: 4px;
                    padding: 10px 14px;
                }
            """)

    def mousePressEvent(self, event):
        """点击时计算光标所在的英文单词。"""
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        # 获取纯文本和点击位置
        plain = self._strip_html(self.text())
        if not plain:
            super().mousePressEvent(event)
            return

        fm = QFontMetrics(self.font())
        x = event.pos().x() - 14  # 减去左 padding
        y = event.pos().y() - 10  # 减去上 padding

        if x < 0 or y < 0:
            super().mousePressEvent(event)
            return

        # 找到点击位置对应的字符索引
        char_idx = self._char_at_position(plain, fm, x, y, self.width() - 28)
        if char_idx < 0:
            super().mousePressEvent(event)
            return

        # 前后扩展到单词边界
        word = self._extract_word(plain, char_idx)
        if word and len(word) >= 3 and word.lower() not in STOP_WORDS:
            self.word_clicked.emit(word)

        super().mousePressEvent(event)

    @staticmethod
    def _strip_html(text: str) -> str:
        """去 HTML 标签，返回纯文本。"""
        return re.sub(r'<[^>]+>', '', text).replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

    @staticmethod
    def _char_at_position(text: str, fm: QFontMetrics, x: int, y: int, avail_w: int) -> int:
        """根据像素坐标计算字符索引。"""
        line_h = fm.height()
        line_idx = max(0, y // line_h)
        # 按可用宽度模拟自动换行
        lines = _TappableBubble._wrap_lines(text, fm, avail_w)
        if line_idx >= len(lines):
            return -1
        line = lines[line_idx]
        # 在该行中找 X 对应的字符
        for i in range(len(line)):
            if fm.horizontalAdvance(line[:i+1]) > x:
                # 返回原文中的位置
                return text.find(line, sum(len(l) for l in lines[:line_idx])) if i == 0 else text.find(line[:i]) + i
        return text.find(line) + len(line) - 1 if line else -1

    @staticmethod
    def _wrap_lines(text: str, fm: QFontMetrics, avail_w: int) -> list:
        """模拟 QLabel 自动换行，返回行列表。"""
        lines = []
        current = ""
        for word in text.split(' '):
            test = current + (' ' if current else '') + word
            if fm.horizontalAdvance(test) > avail_w and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines or [text]

    @staticmethod
    def _extract_word(text: str, idx: int) -> str:
        """从文本中提取 idx 位置的完整英文单词。"""
        if idx < 0 or idx >= len(text):
            return ""
        if not text[idx].isalpha() and text[idx] != "'":
            return ""
        # 向前找单词边界
        start = idx
        while start > 0 and (text[start-1].isalpha() or text[start-1] == "'"):
            start -= 1
        # 向后找单词边界
        end = idx
        while end < len(text)-1 and (text[end+1].isalpha() or text[end+1] == "'"):
            end += 1
        return text[start:end+1]


class ChatPage(QWidget):
    """聊天页面 — 两栏布局。"""

    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_id: int | None = None
        self._session_id: int | None = None
        self._topic: str = ""
        self._llm = None
        self._vocab_repo = None
        self._user_vocab_repo = None
        self._chat_session_repo = None
        self._prompt_builder = None
        self._tts = None
        self._conversation_history: list = []
        self._send_debounce_timer = QTimer(self)
        self._send_debounce_timer.setSingleShot(True)
        self._send_debounce_timer.timeout.connect(self._do_send)

        # ── 主布局（两栏）──
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 左栏：对话区 ──
        left_panel = QWidget()
        left_panel.setStyleSheet("background: rgba(255,255,255,100);")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        # 顶部栏
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← 返回")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #7C3AED;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { color: #5B21B6; }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_btn)

        self.topic_label = QLabel("")
        f = QFont(); f.setPixelSize(13); f.setBold(True); self.topic_label.setFont(f)
        self.topic_label.setStyleSheet("color: #1F2937; background: transparent;")
        top_bar.addWidget(self.topic_label)
        top_bar.addStretch()
        left_layout.addLayout(top_bar)

        # 对话气泡区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(6)
        scroll.setWidget(self.chat_content)
        left_layout.addWidget(scroll, stretch=1)

        # 输入区
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("输入你想说的话...（中文或英文）")
        f = QFont(); f.setPixelSize(14); self.input_box.setFont(f)
        self.input_box.setMaximumHeight(60)
        self.input_box.setStyleSheet("""
            QTextEdit {
                background: #F3F4F6; border: 2px solid #E5E7EB;
                border-radius: 12px; padding: 8px 12px; color: #1F2937;
            }
            QTextEdit:focus { background: white; border-color: #7C3AED; }
        """)
        input_layout.addWidget(self.input_box, stretch=1)

        send_btn = QPushButton("发送")
        f = QFont(); f.setPixelSize(13); f.setBold(True); send_btn.setFont(f)
        send_btn.setFixedSize(64, 44)
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.clicked.connect(self._on_send)
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7C3AED, stop:1 #A855F7);
                color: white; border: none; border-radius: 12px;
            }
            QPushButton:pressed { background: #6D28D9; }
        """)
        input_layout.addWidget(send_btn)

        left_layout.addLayout(input_layout)
        main_layout.addWidget(left_panel, stretch=3)

        # ── 右栏：生词面板 ──
        right_panel = QWidget()
        right_panel.setFixedWidth(220)
        right_panel.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,200);
                border-left: 2px solid rgba(124,58,237,40);
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(6)

        word_title = QLabel("📝 生词本")
        f = QFont(); f.setPixelSize(14); f.setBold(True); word_title.setFont(f)
        word_title.setStyleSheet("color: #4C1D95; background: transparent;")
        right_layout.addWidget(word_title)

        self._word_count_label = QLabel("")
        f = QFont(); f.setPixelSize(11); self._word_count_label.setFont(f)
        self._word_count_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        right_layout.addWidget(self._word_count_label)

        self.word_scroll = QScrollArea()
        self.word_scroll.setWidgetResizable(True)
        self.word_list_widget = QWidget()
        self.word_list_widget.setStyleSheet("background: transparent;")
        self.word_list_layout = QVBoxLayout(self.word_list_widget)
        self.word_list_layout.setAlignment(Qt.AlignTop)
        self.word_list_layout.setSpacing(4)
        self.word_scroll.setWidget(self.word_list_widget)
        self.word_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        right_layout.addWidget(self.word_scroll, stretch=1)

        self._show_word_panel_empty()
        main_layout.addWidget(right_panel)

    def start_chat(
        self, user_id: int, session_id: int, topic: str,
        llm, vocab_repo, user_vocab_repo, chat_session_repo,
        prompt_builder=None, tts=None,
    ):
        """开始或恢复一个会话。

        同话题 → 保留对话历史和生词面板。
        不同话题 → 清空后重新开始。
        """
        same_topic = (self._topic == topic)

        self._user_id = user_id
        self._session_id = session_id
        self._topic = topic
        self._llm = llm
        self._vocab_repo = vocab_repo
        self._user_vocab_repo = user_vocab_repo
        self._chat_session_repo = chat_session_repo
        self._prompt_builder = prompt_builder
        self._tts = tts

        self.topic_label.setText(f"话题：{topic}")

        if same_topic:
            # 同话题恢复：不清空对话，只刷新生词面板
            self._clear_word_panel()
            self._refresh_word_panel()
            return

        # 不同话题：清空 + 重新开始
        self._conversation_history = []
        self._clear_chat_area()
        self._clear_word_panel()

        self._send_system_message(
            f"让我们聊聊 <b>{topic}</b> 吧！你想说什么？"
        )

    def _clear_chat_area(self):
        """清空对话区（包括嵌套布局和所有组件）。"""
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item is None:
                continue
            sub_layout = item.layout()
            if sub_layout:
                self._clear_sub_layout(sub_layout)
                continue
            widget = item.widget()
            if widget:
                widget.deleteLater()

    @staticmethod
    def _clear_sub_layout(layout):
        """递归清理嵌套布局中的所有 widget。"""
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            sub = item.layout()
            if sub:
                ChatPage._clear_sub_layout(sub)
                continue
            w = item.widget()
            if w:
                w.deleteLater()

    def _on_send(self):
        """发送按钮（去抖 500ms）。"""
        if self._send_debounce_timer.isActive():
            return
        self._send_debounce_timer.start(500)

    def _do_send(self):
        """实际发送逻辑。"""
        text = self.input_box.toPlainText().strip()
        if not text or not self._llm:
            return
        self.input_box.clear()

        # 用户消息
        self._add_bubble(text, True)
        self._conversation_history.append({"role": "user", "content": text})

        # AI 回复
        self._add_typing_indicator()
        QTimer.singleShot(100, self._get_ai_response)

    def _get_ai_response(self):
        """调用 LLM 获取回复。"""
        topic = self._topic
        system_prompt = self._build_chat_prompt()

        try:
            resp = self._llm.chat(
                system_prompt=system_prompt,
                messages=self._conversation_history[-6:],  # 最近 6 轮
            )
            reply_text = resp.text if resp else "Sorry, I didn't catch that."
        except Exception:
            reply_text = "(网络问题，请重试)"

        self._remove_typing_indicator()
        self._add_bubble(reply_text, False)
        self._conversation_history.append({"role": "assistant", "content": reply_text})

        QTimer.singleShot(50, self._scroll_to_bottom)

    def _build_chat_prompt(self) -> str:
        """构建聊天系统提示词。"""
        topic = self._topic

        # 从 user_repo 获取英语水平（如果有）
        level = "middle"
        if self._user_id:
            from line_c.config import DATABASE_PATH
            from line_c.engine.user_repository import UserRepository
            try:
                ur = UserRepository(DATABASE_PATH)
                p = ur.get_by_id(self._user_id)
                if p:
                    level = p.english_level
                ur.close()
            except Exception:
                pass

        persona = {
            "beginner": "a patient English teacher. Use very simple English, short sentences under 20 words. Be encouraging.",
            "primary": "a supportive language partner. Use basic vocabulary, sentences under 30 words.",
            "middle": "a friendly English-speaking companion chatting naturally. Use everyday vocabulary, sentences under 40 words.",
            "high": "a knowledgeable conversation partner. Discuss complex topics naturally with rich vocabulary.",
            "advanced": "a native-level conversation partner. Use idioms, cultural references, and sophisticated vocabulary naturally.",
        }.get(level, "a friendly English-speaking companion.")

        return f"""You are Leo, {persona}

## Conversation Topic
{topic}

## Important Rules
1. ALWAYS respond in English. This is an English learning tool.
2. Keep responses conversational — like chatting over coffee, not a textbook.
3. Ask follow-up questions to keep the conversation flowing.
4. If your partner writes in Chinese, gently help rephrase their message in English as part of your response.
5. Do NOT lecture or sound like a teacher (unless your partner is a complete beginner).
6. Stay on the topic of "{topic}" but let the conversation flow naturally.
7. Do NOT generate content about politics, violence, or adult topics.
8. Keep your response under 50 words."""

    def _add_bubble(self, text: str, is_user: bool):
        """添加一个聊天气泡。"""
        bubble = _TappableBubble(text, is_user)
        bubble.word_clicked.connect(self._on_word_clicked)

        wrapper = QHBoxLayout()
        wrapper.setSpacing(0)
        if is_user:
            wrapper.addStretch()
            wrapper.addWidget(bubble)
        else:
            wrapper.addWidget(bubble)
            wrapper.addStretch()

        self.chat_layout.addLayout(wrapper)

    def _add_typing_indicator(self):
        """显示输入指示器。"""
        self._typing_label = QLabel("Leo 正在输入...")
        f = QFont(); f.setPixelSize(11); f.setBold(True); self._typing_label.setFont(f)
        self._typing_label.setStyleSheet("color: #7C3AED; background: transparent; padding: 4px 40px;")
        self.chat_layout.addWidget(self._typing_label)

    def _remove_typing_indicator(self):
        """移除输入指示器。"""
        if hasattr(self, '_typing_label') and self._typing_label:
            self._typing_label.deleteLater()
            self._typing_label = None

    def _send_system_message(self, text: str):
        """显示系统消息。"""
        label = QLabel(text)
        f = QFont(); f.setPixelSize(13); label.setFont(f)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                background: #EDE9FE; color: #4C1D95;
                border-radius: 12px; padding: 12px 16px;
            }
        """)
        wrapper = QHBoxLayout()
        wrapper.addWidget(label)
        wrapper.addStretch()
        self.chat_layout.addLayout(wrapper)

    def _on_word_clicked(self, word: str):
        """用户点击气泡中的单词 → 弹窗，由用户决定是否加入生词。"""
        if not self._user_id:
            return

        popup = WordPopup(
            word=word,
            user_id=self._user_id,
            vocab_repo=self._vocab_repo,
            user_vocab_repo=self._user_vocab_repo,
            session_id=self._session_id,
            llm=self._llm,
            parent=self,
        )
        popup.exec_()
        # 只有用户点了"加入生词本"才刷新生词面板
        if popup.was_added():
            self._refresh_word_panel()

    def _refresh_word_panel(self):
        """刷新右侧生词面板。"""
        self._clear_word_panel()
        if not self._user_id:
            return

        words = self._user_vocab_repo.get_by_session(self._session_id) if self._session_id else []
        if not words:
            words = self._user_vocab_repo.get_by_user(self._user_id)
            words = [w for w in words if w.get("state") == "NEW"]

        if not words:
            self._show_word_panel_empty()
            return

        self._word_count_label.setText(f"本次收集 {len(words)} 个生词")

        for w in words:
            card = self._make_word_card(w)
            self.word_list_layout.addWidget(card)

    def _make_word_card(self, data: dict) -> QFrame:
        """创建单个生词卡片。"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: white; border-radius: 8px;
                border: 1px solid rgba(124,58,237,15);
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        word_label = QLabel(data.get("word", ""))
        f = QFont(); f.setPixelSize(12); f.setBold(True); word_label.setFont(f)
        word_label.setStyleSheet("color: #1F2937; background: transparent;")
        layout.addWidget(word_label)

        layout.addStretch()

        count = data.get("lookup_count", 1)
        if count > 1:
            cnt_label = QLabel(f"×{count}")
            f = QFont(); f.setPixelSize(10); cnt_label.setFont(f)
            cnt_label.setStyleSheet("color: #9CA3AF; background: transparent;")
            layout.addWidget(cnt_label)

        return card

    def _clear_word_panel(self):
        """清空生词面板。"""
        while self.word_list_layout.count():
            item = self.word_list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._word_count_label.setText("")

    def _show_word_panel_empty(self):
        hint = QLabel("对话中点击不认识的\n单词即可查释义\n\n生词会自动出现在这里")
        f = QFont(); f.setPixelSize(11); hint.setFont(f)
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9CA3AF; background: transparent;")
        self.word_list_layout.addWidget(hint)

    def _scroll_to_bottom(self):
        scroll = self.findChild(QScrollArea)
        if scroll:
            sb = scroll.verticalScrollBar()
            sb.setValue(sb.maximum())
