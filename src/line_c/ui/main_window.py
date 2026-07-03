"""主窗口 — v2 多页面导航壳。

4 页面结构 (QStackedWidget):
  [0] HomePage — 角色选择/创建
  [1] TopicFeedPage — 话题选择
  [2] ChatPage — 聊天
  [3] ReviewPage — 生词复习

主窗口只负责导航和依赖传递，不包含业务逻辑。
"""

from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QWidget
from PyQt5.QtCore import pyqtSignal

from .pages.home_page import HomePage
from .pages.topic_feed_page import TopicFeedPage
from .pages.chat_page import ChatPage
from .pages.review_page import ReviewPage


class MainWindow(QMainWindow):
    """应用主窗口 — 页面导航壳。"""

    # 信号：当前活跃用户变化
    current_user_changed = pyqtSignal(int)

    def __init__(
        self,
        user_repo,
        chat_session_repo,
        user_vocab_repo,
        vocab_repo,
        llm,
        tts=None,
        parent=None,
    ):
        super().__init__(parent)

        # 依赖注入
        self.user_repo = user_repo
        self.chat_session_repo = chat_session_repo
        self.user_vocab_repo = user_vocab_repo
        self.vocab_repo = vocab_repo
        self.llm = llm
        self.tts = tts

        # 当前状态
        self._current_user_id: int | None = None
        self._current_session_id: int | None = None

        # ── 窗口设置 ──
        self.setWindowTitle("VocaLand — AI 英语学习伙伴")
        self.resize(1000, 600)
        self.setMinimumSize(800, 500)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #F3E8FF, stop:1 #F9FAFB
                );
            }
        """)

        # ── QStackedWidget ──
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # ── 创建四个页面 ──
        self.home_page = HomePage(user_repo=self.user_repo)
        self.topic_feed_page = TopicFeedPage()
        self.chat_page = ChatPage()
        self.review_page = ReviewPage()

        self.stack.addWidget(self.home_page)       # index 0
        self.stack.addWidget(self.topic_feed_page)  # index 1
        self.stack.addWidget(self.chat_page)        # index 2
        self.stack.addWidget(self.review_page)      # index 3

        # ── 连接页面信号 ──
        # 首页：选择角色 → 进入话题页
        self.home_page.character_selected.connect(self._on_character_selected)
        self.home_page.character_created.connect(self._on_character_created)

        # 话题页：选择话题 → 进入聊天页
        self.topic_feed_page.topic_selected.connect(self._on_topic_selected)
        self.topic_feed_page.custom_topic_submitted.connect(self._on_custom_topic)
        self.topic_feed_page.review_requested.connect(self._on_review_requested)
        self.topic_feed_page.back_requested.connect(lambda: self.switch_to_page(0))

        # 聊天页：返回 → 回到话题页
        self.chat_page.back_requested.connect(self._on_chat_back)

        # 复习页：返回 → 回到话题页
        self.review_page.back_requested.connect(lambda: self.switch_to_page(1))

    # ── 导航 ──

    def switch_to_page(self, index: int):
        """切换当前页面。0=首页, 1=话题, 2=聊天, 3=复习"""
        self.stack.setCurrentIndex(index)

    def set_current_user(self, user_id: int):
        """设置当前活跃角色。"""
        self._current_user_id = user_id
        self.current_user_changed.emit(user_id)

    def get_current_user(self) -> int | None:
        return self._current_user_id

    # ── 页面间导航回调 ──

    def _on_character_selected(self, user_id: int):
        """首页选择已有角色 → 进入话题页。"""
        self.set_current_user(user_id)
        profile = self.user_repo.get_by_id(user_id)
        # 后面 Phase 2 会在这里加载话题
        self.topic_feed_page.set_user(user_id, profile)
        self.switch_to_page(1)

    def _on_character_created(self, user_id: int):
        """新建角色成功 → 进入话题页。"""
        self.set_current_user(user_id)
        profile = self.user_repo.get_by_id(user_id)
        self.topic_feed_page.set_user(user_id, profile)
        self.switch_to_page(1)

    def _on_topic_selected(self, topic_title: str):
        """话题页选择话题 → 创建会话 → 进入聊天页。"""
        topic_title = topic_title.strip()

        # 同话题恢复：新会话（用于生词追踪）但不重建聊天
        if (self._current_user_id is not None
                and self.chat_page._topic == topic_title):
            from line_c.domain.chat_session import ChatSession
            session = ChatSession(
                user_id=self._current_user_id,
                topic_title=topic_title,
                topic_source="llm",
            )
            self._current_session_id = self.chat_session_repo.create(session)
            # 只更新 session_id，不清空消息
            self.chat_page._session_id = self._current_session_id
            self.chat_page._refresh_word_panel()
            self.switch_to_page(2)
            return

        # 不同话题：创建新会话
        from line_c.domain.chat_session import ChatSession
        session = ChatSession(
            user_id=self._current_user_id,
            topic_title=topic_title,
            topic_source="llm",
        )
        self._current_session_id = self.chat_session_repo.create(session)
        self.chat_page.start_chat(
            user_id=self._current_user_id,
            session_id=self._current_session_id,
            topic=topic_title,
            llm=self.llm,
            vocab_repo=self.vocab_repo,
            user_vocab_repo=self.user_vocab_repo,
            chat_session_repo=self.chat_session_repo,
            tts=self.tts,
        )
        self.switch_to_page(2)

    def _on_custom_topic(self, topic_title: str):
        """自定义话题 → 同话题选择流程。"""
        self._on_topic_selected(topic_title)

    def _on_review_requested(self):
        """话题页点击进入复习 → 复习页。"""
        self.review_page.start_review(
            user_id=self._current_user_id,
            user_vocab_repo=self.user_vocab_repo,
        )
        self.switch_to_page(3)

    def _on_chat_back(self):
        """聊天页返回 → 结束会话 → 回话题页。"""
        if self._current_session_id:
            self.chat_session_repo.end_session(self._current_session_id)
            self._current_session_id = None
        # 刷新话题页
        if self._current_user_id:
            profile = self.user_repo.get_by_id(self._current_user_id)
            self.topic_feed_page.set_user(self._current_user_id, profile)
        self.switch_to_page(1)
