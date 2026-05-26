"""聊天气泡组件（VocaAI 风格）。

- 用户气泡：浅绿背景，右对齐，圆角（左上大圆角 + 右上小圆角）
- AI 气泡：白色背景，左对齐，带小头像，圆角（右上大圆角 + 左上小圆角）
"""

from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ChatBubble(QWidget):
    """单个聊天气泡。

    用法：
        bubble = ChatBubble("Hello!", is_user=True)
        layout.addWidget(bubble)
    """

    def __init__(self, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setMaximumWidth(340)
        f = QFont(); f.setPixelSize(14); label.setFont(f)
        label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        if is_user:
            # 用户气泡：浅绿，靠右
            label.setStyleSheet("""
                QLabel {
                    background-color: #DCFCE7;
                    color: #14532D;
                    border: 1px solid #BBF7D0;
                    border-radius: 16px;
                    border-top-right-radius: 4px;
                    padding: 10px 14px;
                }
            """)
            layout.addStretch()
            layout.addWidget(label)

        else:
            # AI 气泡：白色卡片 + 左侧小头像
            mini_avatar = QLabel("L")
            mini_avatar.setFixedSize(28, 28)
            mini_avatar.setAlignment(Qt.AlignCenter)
            f = QFont()
            f.setPixelSize(13)
            f.setBold(True)
            mini_avatar.setFont(f)
            mini_avatar.setStyleSheet("""
                QLabel {
                    background: #F08A3E;
                    color: white;
                    border-radius: 14px;
                    border: 1px solid #E5E7EB;
                }
            """)
            mini_avatar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            label.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    border: 1px solid #E5E7EB;
                    border-radius: 16px;
                    border-top-left-radius: 4px;
                    padding: 10px 14px;
                }
            """)

            layout.addWidget(mini_avatar, alignment=Qt.AlignTop)
            layout.addWidget(label)
            layout.addStretch()


class TypingIndicator(QWidget):
    """"正在输入..."跳动点指示器。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 4, 0, 4)
        layout.setSpacing(4)

        text = QLabel("Leo 正在输入")
        f = QFont(); f.setPixelSize(11); f.setBold(True); text.setFont(f)
        text.setStyleSheet("color: #8B5CF6; background: transparent;")
        layout.addWidget(text)

        self._dots = []
        for i in range(3):
            dot = QLabel("●")
            df = QFont(); df.setPixelSize(10); dot.setFont(df)
            dot.setStyleSheet("color: #A855F7; background: transparent;")
            dot.setFixedSize(12, 12)
            dot.setAlignment(Qt.AlignCenter)
            self._dots.append(dot)
            layout.addWidget(dot)

        layout.addStretch()
        self.hide()
