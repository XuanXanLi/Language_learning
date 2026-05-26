"""主窗口 — 横屏 VocaAI 风格。

布局（16:9 横屏）：
┌──────────┬───────────────────────────────┬──────────┐
│          │                               │          │
│  IP 角色  │        对话气泡区               │ 词汇追踪  │
│  30%     │           45%                 │  25%     │
│          │                               │          │
├──────────┴───────────────────────────────┴──────────┤
│  [输入框                              🎤  发送]     │
└─────────────────────────────────────────────────────┘
"""

from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QTextEdit, QPushButton, QScrollArea, QLabel, QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from .chat_bubble import ChatBubble, TypingIndicator
from .character_widget import CharacterWidget
from .word_summary import WordSummary


# ── 配色 ──
PRIMARY_START = "#7C3AED"
PRIMARY_END = "#A855F7"
PRIMARY_DARK = "#6D28D9"
BG_LEFT = "rgba(255, 255, 255, 180)"
BG_MID = "rgba(255, 255, 255, 100)"
BG_RIGHT = "rgba(255, 255, 255, 200)"
BORDER_COLOR = "rgba(124, 58, 237, 40)"


class MainWindow(QMainWindow):
    """应用主窗口 — 横屏 16:9 布局。"""

    def __init__(self, conversation_manager, parent=None):
        super().__init__(parent)
        self.manager = conversation_manager

        self.setWindowTitle("VocaLand — AI 英语学习伙伴")
        self.resize(1000, 600)
        self.setMinimumSize(800, 500)

        # ── 全局背景 ──
        self.setStyleSheet(f"""
            QMainWindow {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #F3E8FF, stop:1 #F9FAFB
                );
            }}
        """)

        # ── 中央 Widget ──
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 上半部分：三栏并排 ──
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(0)

        # 左栏：IP 角色区 (30%)
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_panel.setStyleSheet(f"""
            QWidget {{
                background: {BG_LEFT};
                border-right: 2px solid {BORDER_COLOR};
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.character = CharacterWidget()
        left_layout.addWidget(self.character)

        top_row.addWidget(left_panel)

        # 中栏：对话气泡区 (占剩余宽度的 ~64%)
        mid_panel = QWidget()
        mid_panel.setStyleSheet(f"background: {BG_MID};")
        mid_layout = QVBoxLayout(mid_panel)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)

        # 对话气泡列表
        self.chat_list = QVBoxLayout()
        self.chat_list.setAlignment(Qt.AlignTop)
        self.chat_list.setSpacing(2)

        chat_content = QWidget()
        chat_content.setLayout(self.chat_list)
        chat_content.setStyleSheet("background: transparent;")

        chat_scroll = QScrollArea()
        chat_scroll.setWidgetResizable(True)
        chat_scroll.setWidget(chat_content)
        chat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        mid_layout.addWidget(chat_scroll, stretch=1)

        # 输入指示器
        self.typing_indicator = TypingIndicator()
        mid_layout.addWidget(self.typing_indicator)
        mid_layout.addSpacing(8)

        top_row.addWidget(mid_panel, stretch=1)

        # 右栏：词汇追踪区 (25%)
        right_panel = QWidget()
        right_panel.setFixedWidth(250)
        right_panel.setStyleSheet(f"""
            QWidget {{
                background: {BG_RIGHT};
                border-left: 2px solid {BORDER_COLOR};
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.word_summary = WordSummary()
        right_layout.addWidget(self.word_summary)

        top_row.addWidget(right_panel)

        root.addLayout(top_row, stretch=1)

        # ── 底部分割线 ──
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"QFrame {{ color: {BORDER_COLOR}; border-width: 1px; }}")
        divider.setFixedHeight(2)
        root.addWidget(divider)

        # ── 底部输入区 ──
        input_bar = QWidget()
        input_bar.setFixedHeight(70)
        input_bar.setStyleSheet("background: white;")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(16, 10, 16, 10)
        input_layout.setSpacing(10)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("输入或说出你想说的话...")
        f = QFont(); f.setPixelSize(14); self.input_box.setFont(f)
        self.input_box.setMaximumHeight(48)
        self.input_box.setStyleSheet("""
            QTextEdit {
                background: #F3F4F6;
                border: 2px solid #E5E7EB;
                border-radius: 16px;
                padding: 8px 14px;
                color: #1F2937;
            }
            QTextEdit:focus {
                background: white;
                border-color: #A855F7;
            }
        """)
        input_layout.addWidget(self.input_box, stretch=1)

        # 麦克风按钮
        mic_btn = QPushButton("🎤")
        f = QFont(); f.setPixelSize(18); mic_btn.setFont(f)
        mic_btn.setFixedSize(48, 48)
        mic_btn.setCursor(Qt.PointingHandCursor)
        mic_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                border: 2px solid #E5E7EB;
                border-radius: 14px;
                color: #4B5563;
            }
            QPushButton:pressed {
                background: #E5E7EB;
            }
        """)
        input_layout.addWidget(mic_btn)

        # 发送按钮
        send_btn = QPushButton("发送")
        f = QFont(); f.setPixelSize(14); f.setBold(True); send_btn.setFont(f)
        send_btn.setFixedHeight(48)
        send_btn.setMinimumWidth(80)
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PRIMARY_START}, stop:1 {PRIMARY_END});
                color: white;
                border: none;
                border-bottom: 4px solid {PRIMARY_DARK};
                border-radius: 14px;
                padding: 8px 20px;
            }}
            QPushButton:pressed {{
                border-bottom-width: 2px;
                padding-top: 10px;
            }}
        """)
        send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(send_btn)

        root.addWidget(input_bar)

        # ── 信号连接 ──
        self.manager.message_received.connect(self._add_bubble)
        self.manager.status_changed.connect(self._on_status_changed)
        self.manager.word_event.connect(self.word_summary.on_word_event)

        # 启动后显示欢迎消息
        QTimer.singleShot(100, self._show_welcome)

    # ── 公开接口 ──

    def _show_welcome(self):
        """显示启动欢迎消息。"""
        topic = getattr(self.manager, 'topic', '日常')
        welcome_text = (
            f"Welcome aboard! Let's chat about <b>{topic}</b> today. "
            f"Have you ever been abroad?"
        )
        self._add_bubble(welcome_text, False)

    # ── 内部逻辑 ──

    def _on_send(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        self.input_box.clear()
        self.manager.handle_user_message(text)

    def _add_bubble(self, text: str, is_user: bool):
        bubble = ChatBubble(text, is_user)
        self.chat_list.addWidget(bubble)
        QTimer.singleShot(50, self._scroll_chat_to_bottom)

    def _scroll_chat_to_bottom(self):
        # 找到 chat_list 所属的 QScrollArea 并滚到底部
        scroll = self.findChild(QScrollArea)
        if scroll:
            sb = scroll.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_status_changed(self, status: str):
        """状态变化 → 更新角色动画 + 输入指示器。"""
        self.character.set_status(status)

        if status == "thinking":
            self.typing_indicator.show()
        else:
            self.typing_indicator.hide()
