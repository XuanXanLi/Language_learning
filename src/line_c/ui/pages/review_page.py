"""复习页 — 墨墨式闪卡复习。

正面：单词 + "点击显示答案"
背面：中文释义 + 英文释义 + 三个自评按钮
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class ReviewPage(QWidget):
    """生词复习页面。"""

    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_id: int | None = None
        self._user_vocab_repo = None
        self._review_mgr = None  # ReviewSessionManager
        self._cards = []
        self._current_idx = 0
        self._flipped = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 20, 32, 20)
        layout.setSpacing(16)

        # 顶部栏
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← 返回话题列表")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.back_requested.emit)
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #7C3AED;
                font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { color: #5B21B6; }
        """)
        top_bar.addWidget(back_btn)
        top_bar.addStretch()

        self.progress_label = QLabel("")
        f = QFont(); f.setPixelSize(13); self.progress_label.setFont(f)
        self.progress_label.setStyleSheet("color: #6B7280; background: transparent;")
        top_bar.addWidget(self.progress_label)
        layout.addLayout(top_bar)

        # 卡片区域
        self.card = QFrame()
        self.card.setFixedHeight(280)
        self.card.setMinimumWidth(400)
        self.card.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 20px;
                border: 2px solid #E5E7EB;
            }
        """)

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setAlignment(Qt.AlignCenter)
        self.card_layout.setSpacing(10)

        self.word_label = QLabel("")
        f = QFont(); f.setPixelSize(28); f.setBold(True); self.word_label.setFont(f)
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setStyleSheet("color: #1F2937; background: transparent;")
        self.card_layout.addWidget(self.word_label)

        self.phonetic_label = QLabel("")
        f = QFont(); f.setPixelSize(14); self.phonetic_label.setFont(f)
        self.phonetic_label.setAlignment(Qt.AlignCenter)
        self.phonetic_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        self.card_layout.addWidget(self.phonetic_label)

        self.definition_label = QLabel("")
        f = QFont(); f.setPixelSize(16); self.definition_label.setFont(f)
        self.definition_label.setAlignment(Qt.AlignCenter)
        self.definition_label.setWordWrap(True)
        self.definition_label.setStyleSheet("color: #1F2937; background: transparent;")
        self.definition_label.hide()
        self.card_layout.addWidget(self.definition_label)

        self.hint_label = QLabel("点击显示释义")
        f = QFont(); f.setPixelSize(13); self.hint_label.setFont(f)
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("color: #A855F7; background: transparent;")
        self.card_layout.addWidget(self.hint_label)

        # 点击卡片翻转
        self.card.mousePressEvent = self._on_card_click

        card_wrapper = QHBoxLayout()
        card_wrapper.addStretch()
        card_wrapper.addWidget(self.card)
        card_wrapper.addStretch()
        layout.addLayout(card_wrapper, stretch=1)

        # 自评按钮
        self.rating_layout = QHBoxLayout()
        self.rating_layout.setSpacing(16)

        self.forgot_btn = QPushButton("没想起来")
        self.forgot_btn.setCursor(Qt.PointingHandCursor)
        self.forgot_btn.clicked.connect(lambda: self._rate(0))
        self.forgot_btn.setStyleSheet("""
            QPushButton {
                background: #FEE2E2; color: #991B1B; border: 2px solid #FECACA;
                border-radius: 14px; padding: 12px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #FECACA; }
        """)
        self.forgot_btn.hide()

        self.hard_btn = QPushButton("有点模糊")
        self.hard_btn.setCursor(Qt.PointingHandCursor)
        self.hard_btn.clicked.connect(lambda: self._rate(3))
        self.hard_btn.setStyleSheet("""
            QPushButton {
                background: #FEF3C7; color: #92400E; border: 2px solid #FDE68A;
                border-radius: 14px; padding: 12px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #FDE68A; }
        """)
        self.hard_btn.hide()

        self.good_btn = QPushButton("想起来了")
        self.good_btn.setCursor(Qt.PointingHandCursor)
        self.good_btn.clicked.connect(lambda: self._rate(5))
        self.good_btn.setStyleSheet("""
            QPushButton {
                background: #D1FAE5; color: #065F46; border: 2px solid #A7F3D0;
                border-radius: 14px; padding: 12px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #A7F3D0; }
        """)
        self.good_btn.hide()

        btn_wrapper = QHBoxLayout()
        btn_wrapper.addStretch()
        btn_wrapper.addWidget(self.forgot_btn)
        btn_wrapper.addWidget(self.hard_btn)
        btn_wrapper.addWidget(self.good_btn)
        btn_wrapper.addStretch()
        self.rating_layout = btn_wrapper
        layout.addLayout(self.rating_layout)

        # 完成总结标签
        self.summary_label = QLabel("")
        f = QFont(); f.setPixelSize(15); self.summary_label.setFont(f)
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #4C1D95; background: transparent;")
        self.summary_label.hide()
        self.card_layout.addWidget(self.summary_label)

    def start_review(self, user_id: int, user_vocab_repo):
        """开始复习会话。"""
        self._user_id = user_id
        self._user_vocab_repo = user_vocab_repo

        from line_c.engine.review_session_manager import ReviewSessionManager
        self._review_mgr = ReviewSessionManager(user_id, user_vocab_repo)
        count = self._review_mgr.load_queue(limit=20)

        if count == 0:
            self._show_empty()
            return

        self.summary_label.hide()
        self.card.show()
        self.forgot_btn.show()
        self.hard_btn.show()
        self.good_btn.show()
        self._show_card_front()

    def _show_empty(self):
        """显示空状态。"""
        self.card.hide()
        self.forgot_btn.hide()
        self.hard_btn.hide()
        self.good_btn.hide()
        self.progress_label.setText("")

        total = self._user_vocab_repo.get_total_count(self._user_id) if self._user_id else 0
        mastered = self._user_vocab_repo.get_mastered_count(self._user_id) if self._user_id else 0

        msg = "还没有生词\n去聊个话题吧！"
        if total > 0:
            msg = f"全部完成！\n\n累计 {total} 词 | 已掌握 {mastered} 词"
        self.summary_label.setText(msg)
        self.summary_label.show()

    def _show_card_front(self):
        """显示卡片正面。"""
        self._flipped = False
        card = self._review_mgr.current_card()
        if not card:
            self._show_complete()
            return

        word = card.get("word", "")
        self.word_label.setText(word)

        # 尝试从 vocab_repo 获取音标
        self.phonetic_label.setText("")

        self.definition_label.hide()
        self.hint_label.setText("点击显示释义")
        self.hint_label.show()

        idx, total = self._review_mgr.progress()
        self.progress_label.setText(f"卡片 {idx} / {total}")

        # 按钮保持可见但建议先翻卡
        self.forgot_btn.show()
        self.hard_btn.show()
        self.good_btn.show()

    def _on_card_click(self, event):
        """点击卡片翻转。"""
        if not self._review_mgr or self._flipped:
            return
        card = self._review_mgr.current_card()
        if not card:
            return

        self._flipped = True

        word = card.get("word", "")
        # 查本地词典获取释义
        definition_cn = ""
        definition_en = ""
        try:
            from line_c.config import DATABASE_PATH
            from line_c.engine.vocabulary_repository import VocabularyRepository
            vr = VocabularyRepository(DATABASE_PATH)
            db_word = vr.get_word(word)
            if db_word:
                definition_cn = db_word.definition_cn
                definition_en = db_word.definition_en
            vr.close()
        except Exception:
            pass

        self.word_label.setText(word)
        text = f"<b>{definition_cn or '释义暂缺'}</b>"
        if definition_en:
            text += f"<br><br><span style='color:#6B7280;font-size:13px;'>{definition_en}</span>"
        self.definition_label.setText(text)
        self.definition_label.show()
        self.hint_label.hide()

    def _rate(self, quality: int):
        """自评并切到下一张。"""
        if not self._review_mgr or not self._flipped:
            return

        result = self._review_mgr.rate_current(quality)

        if result.get("is_last"):
            self._show_complete()
        else:
            self._show_card_front()

    def _show_complete(self):
        """复习完成。"""
        stats = self._review_mgr.get_stats() if self._review_mgr else {}
        mastered = self._review_mgr.get_mastered_count() if self._review_mgr else 0

        msg = f"复习完成！\n\n"
        msg += f"想起来了 {stats.get('remembered', 0)} 词 | "
        msg += f"有点模糊 {stats.get('hard', 0)} 词 | "
        msg += f"还需努力 {stats.get('forgot', 0)} 词\n"
        msg += f"\n累计已掌握 {mastered} 词"

        self.card.hide()
        self.forgot_btn.hide()
        self.hard_btn.hide()
        self.good_btn.hide()

        self.summary_label.setText(msg)
        self.summary_label.show()
        self.progress_label.setText("")
