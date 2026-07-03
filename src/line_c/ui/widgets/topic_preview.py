"""话题预览弹窗。

点击话题卡片后弹出，展示 AI 中文摘要 + 英语讨论引导问题。
用户确认后进入对话，或返回话题列表。
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QScrollArea, QWidget, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class TopicPreviewDialog(QDialog):
    """话题预览弹窗（模态）。"""

    start_chat = pyqtSignal()   # 用户点击「开始对话」
    skip = pyqtSignal()         # 用户点击「换一个」

    def __init__(self, topic, parent=None):
        """
        topic: TopicCard 对象，必须包含：
          - title: 话题标题
          - summary: 原始摘要
          - summary_cn: AI 生成的中文摘要（可能为空）
          - discussion_guide: 英语讨论引导问题列表（可能为空）
          - source: 来源标签
        """
        super().__init__(parent)
        self.setWindowTitle("话题预览")
        self.setMinimumSize(420, 520)
        self.setMaximumSize(560, 800)
        self.setStyleSheet("QDialog { background: #FAFAFA; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 12)
        layout.setSpacing(8)

        # ── 标题 ──
        title_label = QLabel(topic.title)
        f = QFont(); f.setPixelSize(16); f.setBold(True); title_label.setFont(f)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #1F2937; background: transparent;")
        layout.addWidget(title_label)

        # 来源行
        source_label = QLabel(topic.source)
        f = QFont(); f.setPixelSize(10); source_label.setFont(f)
        source_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(source_label)

        # ── 分隔线 ──
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("QFrame { color: #E5E7EB; }")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # ── 可滚动内容区（摘要 + 讨论引导）──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(10)

        # 摘要标题
        cn_title = QLabel("📖 内容摘要")
        f = QFont(); f.setPixelSize(12); f.setBold(True); cn_title.setFont(f)
        cn_title.setStyleSheet("color: #374151; background: transparent;")
        inner_layout.addWidget(cn_title)

        # 摘要内容
        cn_text = topic.summary_cn if topic.summary_cn else topic.summary
        summary_label = QLabel(cn_text)
        summary_label.setWordWrap(True)
        f = QFont(); f.setPixelSize(12); summary_label.setFont(f)
        summary_label.setStyleSheet("color: #4B5563; background: transparent; padding: 4px 0;")
        summary_label.setAlignment(Qt.AlignTop)
        inner_layout.addWidget(summary_label)

        # 讨论引导
        if topic.discussion_guide:
            guide_frame = QFrame()
            guide_frame.setStyleSheet("QFrame { background: #EEF2FF; border-radius: 10px; }")
            guide_layout = QVBoxLayout(guide_frame)
            guide_layout.setContentsMargins(14, 10, 14, 10)
            guide_layout.setSpacing(6)

            guide_title = QLabel("💬 你可以这样聊")
            f = QFont(); f.setPixelSize(12); f.setBold(True); guide_title.setFont(f)
            guide_title.setStyleSheet("color: #4338CA; background: transparent;")
            guide_layout.addWidget(guide_title)

            for q in topic.discussion_guide[:5]:
                q_label = QLabel(f"• {q}")
                q_label.setWordWrap(True)
                f = QFont(); f.setPixelSize(11); q_label.setFont(f)
                q_label.setStyleSheet("color: #3730A3; background: transparent;")
                guide_layout.addWidget(q_label)

            inner_layout.addWidget(guide_frame)

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        # ── 按钮 ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        skip_btn = QPushButton("换一个")
        skip_btn.setCursor(Qt.PointingHandCursor)
        skip_btn.setStyleSheet("""
            QPushButton {
                background: white; border: 2px solid #D1D5DB; border-radius: 10px;
                padding: 10px 24px; font-size: 14px; font-weight: bold; color: #6B7280;
            }
            QPushButton:hover { background: #F3F4F6; border-color: #9CA3AF; }
        """)
        skip_btn.clicked.connect(self.skip.emit)
        skip_btn.clicked.connect(self.close)
        btn_layout.addWidget(skip_btn)

        start_btn = QPushButton("开始对话 →")
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background: #7C3AED; color: white; border: none;
                border-radius: 10px; padding: 10px 28px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #6D28D9; }
        """)
        start_btn.clicked.connect(self.start_chat.emit)
        start_btn.clicked.connect(self.close)
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)
