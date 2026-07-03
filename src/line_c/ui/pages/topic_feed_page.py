"""话题选择页 — 话题 Feed。

显示基于用户兴趣生成的话题摘要卡片。
提供自定义话题入口和复习模式入口。
"""

import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont


class _TopicCard(QFrame):
    """单张话题卡片。"""

    clicked = pyqtSignal(str)  # topic_title

    def __init__(self, title: str, summary: str, source: str = "", summary_cn: str = "", parent=None):
        super().__init__(parent)
        self.topic_title = title
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            _TopicCard {
                background: white;
                border-radius: 14px;
                border: 1px solid #E5E7EB;
            }
            _TopicCard:hover {
                border-color: #7C3AED;
                background: #F5F3FF;
            }
        """)
        self.setFixedHeight(110)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 8)
        layout.setSpacing(4)

        # 第一行：标题 + 来源
        top = QHBoxLayout()
        title_label = QLabel(f"{title}")
        f = QFont(); f.setPixelSize(14); f.setBold(True); title_label.setFont(f)
        title_label.setStyleSheet("color: #1F2937; background: transparent;")
        top.addWidget(title_label)
        top.addStretch()

        if source:
            src = QLabel(source)
            f = QFont(); f.setPixelSize(10); src.setFont(f)
            src.setStyleSheet("color: #9CA3AF; background: transparent;")
            top.addWidget(src)

        layout.addLayout(top)

        # 中文摘要（优先显示）
        display_text = summary_cn if summary_cn else summary[:120]
        summary_label = QLabel(display_text)
        summary_label.setWordWrap(True)
        f = QFont(); f.setPixelSize(11); summary_label.setFont(f)
        summary_label.setStyleSheet("color: #6B7280; background: transparent;")
        layout.addWidget(summary_label)

        layout.addStretch()

        # 开始按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        start_btn = QPushButton("开始 →")
        f = QFont(); f.setPixelSize(11); f.setBold(True); start_btn.setFont(f)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setStyleSheet("""
            QPushButton {
                background: #7C3AED; color: white; border: none;
                border-radius: 8px; padding: 4px 14px;
            }
            QPushButton:hover { background: #6D28D9; }
        """)
        start_btn.clicked.connect(lambda: self.clicked.emit(self.topic_title))
        btn_layout.addWidget(start_btn)
        layout.addLayout(btn_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.topic_title)
        super().mousePressEvent(event)


class TopicFeedPage(QWidget):
    """话题选择页面。"""

    topic_selected = pyqtSignal(str)          # 选了LLM/fallback话题
    custom_topic_submitted = pyqtSignal(str)  # 自定义话题
    review_requested = pyqtSignal()           # 进入复习模式
    back_requested = pyqtSignal()             # 返回首页
    _topics_loaded = pyqtSignal(list)         # 后台话题加载完成（内部信号）

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_id: int | None = None
        self._profile = None  # UserProfile
        self._topic_generator = None  # 注入于 Phase 2 完善
        self._loading = False
        self._topics: list = []     # 当前展示的 TopicCard 列表
        self._timeout_timer = None  # RSS 加载超时计时器

        # 后台线程加载完成后切回主线程
        self._topics_loaded.connect(self._on_topics_arrived)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # 顶部栏
        top_bar = QHBoxLayout()

        back_btn = QPushButton("← 返回首页")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #7C3AED;
                font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { color: #5B21B6; }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(back_btn)
        top_bar.addStretch()

        self.interest_label = QLabel("")
        f = QFont(); f.setPixelSize(12); self.interest_label.setFont(f)
        self.interest_label.setStyleSheet("color: #6B7280; background: transparent;")
        top_bar.addWidget(self.interest_label)

        layout.addLayout(top_bar)

        # 话题卡片区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_widget = QWidget()
        self.cards_widget.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_widget)
        layout.addWidget(scroll, stretch=1)

        # 自定义话题输入
        custom_layout = QHBoxLayout()
        custom_label = QLabel("或者，输入你想聊的任何话题：")
        f = QFont(); f.setPixelSize(12); custom_label.setFont(f)
        custom_label.setStyleSheet("color: #6B7280; background: transparent;")
        custom_layout.addWidget(custom_label)

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("例如：量子计算的未来...")
        self.custom_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E5E7EB; border-radius: 10px;
                padding: 8px 14px; font-size: 13px; background: white;
            }
            QLineEdit:focus { border-color: #7C3AED; }
        """)
        self.custom_input.returnPressed.connect(self._on_custom_submit)
        custom_layout.addWidget(self.custom_input, stretch=1)

        custom_btn = QPushButton("开始对话")
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.clicked.connect(self._on_custom_submit)
        custom_btn.setStyleSheet("""
            QPushButton {
                background: #7C3AED; color: white; border: none;
                border-radius: 10px; padding: 8px 18px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #6D28D9; }
        """)
        custom_layout.addWidget(custom_btn)
        layout.addLayout(custom_layout)

        # 分隔线
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("QFrame { color: #E5E7EB; }")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        # 复习入口
        review_btn = QPushButton("📚 进入生词复习")
        review_btn.setCursor(Qt.PointingHandCursor)
        review_btn.clicked.connect(self.review_requested.emit)
        review_btn.setStyleSheet("""
            QPushButton {
                background: white; border: 2px solid #7C3AED; border-radius: 12px;
                padding: 10px; font-size: 14px; font-weight: bold; color: #7C3AED;
            }
            QPushButton:hover {
                background: #F5F3FF;
            }
        """)
        layout.addWidget(review_btn)

        # 初始加载占位
        self._show_placeholder("选择一个角色后将自动加载话题...")

    def set_user(self, user_id: int, profile):
        """设置当前角色并加载话题（不阻塞 UI）。

        先显示加载动画，30 秒超时后降级到预设话题。
        """
        self._user_id = user_id
        self._profile = profile

        # 兴趣标签
        interest_names = {
            "ai_tech": "AI科技", "finance": "金融财经", "science": "科学知识",
            "history": "历史文化", "travel": "旅游美食", "music": "音乐影视",
            "sports": "体育运动", "games": "游戏动漫",
        }
        tags = ", ".join(interest_names.get(i, i) for i in profile.interests)
        self.interest_label.setText(f"基于你的兴趣：{tags}")

        # 清空旧话题，显示加载动画
        self._topics = []
        self._show_loading()

        # 取消之前的超时计时器
        if self._timeout_timer:
            self._timeout_timer.stop()

        # 启动 30 秒超时计时器
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_rss_timeout)
        self._timeout_timer.start(30000)

        # 后台加载 RSS（防止重复启动）
        if self._topic_generator and not self._loading:
            threading.Thread(target=self._load_topics_async, daemon=True).start()

    def set_topic_generator(self, generator):
        """注入话题生成器。"""
        self._topic_generator = generator

    def _load_topics_async(self):
        """后台线程：加载 RSS 话题（中文源，无需翻译）。"""
        self._loading = True
        topics = []
        try:
            topics = self._topic_generator.generate(
                self._profile.interests, self._profile.english_level
            )
        except Exception:
            pass
        finally:
            self._loading = False

        # 有结果或空结果都通知主线程（主线程决定是否降级到 fallback）
        self._topics_loaded.emit(topics)

    # ── 加载状态管理 ──────────────────────────────────────

    def _on_topics_arrived(self, topics):
        """后台话题加载完成（主线程回调）。"""
        # 停止超时计时器
        if self._timeout_timer:
            self._timeout_timer.stop()
            self._timeout_timer = None

        if topics:
            self._display_topics(topics)
        else:
            self._show_fallback_topics()

    def _on_rss_timeout(self):
        """30 秒超时：降级到预设话题。"""
        self._timeout_timer = None
        if not self._topics:  # 还没显示任何话题 → 显示 fallback
            self._show_fallback_topics()

    def _show_loading(self):
        """显示加载动画。"""
        self._clear_cards()

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setAlignment(Qt.AlignCenter)
        c_layout.setSpacing(8)

        spinner = QLabel("🔄")
        f = QFont(); f.setPixelSize(40); spinner.setFont(f)
        spinner.setAlignment(Qt.AlignCenter)
        spinner.setStyleSheet("color: #7C3AED; background: transparent;")
        c_layout.addWidget(spinner)

        msg = QLabel("正在获取今日热点新闻...")
        f = QFont(); f.setPixelSize(14); msg.setFont(f)
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #374151; background: transparent; padding-top: 12px;")
        c_layout.addWidget(msg)

        hint = QLabel("连接 RSS 新闻源中，最长等待 30 秒")
        f = QFont(); f.setPixelSize(11); hint.setFont(f)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #9CA3AF; background: transparent;")
        c_layout.addWidget(hint)

        self.cards_layout.insertWidget(self.cards_layout.count() - 1, container)

    def _show_fallback_topics(self):
        """显示内置默认话题。"""
        defaults = [
            ("探索人工智能的未来", "AI正在改变各个行业，从医疗到金融。让我们一起讨论AI如何塑造我们的世界。"),
            ("全球金融趋势分析", "数字货币、通货膨胀和投资策略——了解当前的经济格局。"),
            ("科技如何改变日常生活", "从智能手机到智能家居，科技让生活更便捷也带来了新的挑战。"),
            ("旅行中的文化碰撞", "分享旅行经历和文化差异，用英语讲述你的冒险故事。"),
            ("健康生活与科学饮食", "探讨最新的健康研究发现和实用的日常饮食建议。"),
            ("音乐与电影的魅力", "聊聊你最喜欢的音乐类型和电影作品，推荐给彼此。"),
        ]
        self._display_topics([
            type('TopicCard', (), {'title': t, 'summary': s, 'source': '预设'})()
            for t, s in defaults
        ])

    def _display_topics(self, topics):
        """显示话题卡片列表。"""
        self._topics = list(topics)  # 保存原始对象供预览使用
        self._clear_cards()
        for topic in topics:
            card = _TopicCard(
                title=getattr(topic, 'title', str(topic)),
                summary=getattr(topic, 'summary', ''),
                source=getattr(topic, 'source', ''),
                summary_cn=getattr(topic, 'summary_cn', ''),
            )
            card.clicked.connect(lambda checked, t=topic: self._on_card_clicked(t))
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)  # before stretch

    def _on_card_clicked(self, topic):
        """卡片点击 → 生成预览 → 弹窗确认 → 进入对话。"""
        import traceback
        try:
            # 生成预览内容（Cloud 模式调 LLM，Mock 模式用模板，同步调用）
            if self._topic_generator:
                topic = self._topic_generator.generate_preview(topic)

            # 弹预览窗
            from line_c.ui.widgets.topic_preview import TopicPreviewDialog
            dialog = TopicPreviewDialog(topic, parent=self)
            dialog.start_chat.connect(lambda: self.topic_selected.emit(topic.title))
            dialog.exec_()
        except Exception as e:
            traceback.print_exc()
            raise

    def _show_placeholder(self, text: str):
        """显示占位文本。"""
        self._clear_cards()
        placeholder = QLabel(text)
        f = QFont(); f.setPixelSize(14); placeholder.setFont(f)
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #9CA3AF; background: transparent; padding: 40px;")
        self.cards_layout.insertWidget(0, placeholder)

    def _clear_cards(self):
        """清空卡片区域。"""
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

    def _on_custom_submit(self):
        text = self.custom_input.text().strip()
        if text:
            self.custom_input.clear()
            self.custom_topic_submitted.emit(text)
