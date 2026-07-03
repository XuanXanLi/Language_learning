"""单词释义弹窗。

点击聊天气泡中的单词 → 弹出此弹窗。
查词流程: 本地SQLite词典 → CloudLLM兜底 → "暂不可用"提示。
用户决定是否加入生词本。
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class WordPopup(QDialog):
    """单词释义弹窗（模态）。用户主动选择是否加入生词本。"""

    word_saved = pyqtSignal(str)  # 用户点击"加入生词本"后发射

    def __init__(
        self,
        word: str,
        user_id: int,
        vocab_repo,           # VocabularyRepository (词典)
        user_vocab_repo,      # UserVocabularyRepository
        session_id: int | None = None,
        llm=None,             # CloudLLM 兜底查词
        parent=None,
    ):
        super().__init__(parent)
        self._word = word
        self._user_id = user_id
        self._user_vocab_repo = user_vocab_repo
        self._session_id = session_id
        self._added = False  # 本次弹窗是否加入了生词本

        self.setWindowTitle(f"📖 {word}")
        self.setMinimumSize(360, 320)
        self.setMaximumSize(480, 520)
        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # ── 查词 ──
        word_data = self._lookup(word, vocab_repo, llm)

        # ── 单词 + 音标 + 词性 ──
        header = QHBoxLayout()
        word_label = QLabel(word)
        f = QFont(); f.setPixelSize(22); f.setBold(True); word_label.setFont(f)
        word_label.setStyleSheet("color: #1F2937; background: transparent;")
        header.addWidget(word_label)

        phonetic = word_data.get("phonetic", "")
        pos = word_data.get("pos", "")
        if phonetic or pos:
            meta = QLabel(f"{phonetic}  {pos}")
            f = QFont(); f.setPixelSize(13); meta.setFont(f)
            meta.setStyleSheet("color: #9CA3AF; background: transparent;")
            header.addWidget(meta)
        header.addStretch()
        layout.addLayout(header)

        # ── 分隔线 ──
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #E5E7EB;")
        layout.addWidget(sep)

        # ── 中文释义 ──
        cn_def = word_data.get("definition_cn", "")
        if cn_def:
            cn_label = QLabel(f"中文：{cn_def}")
            f = QFont(); f.setPixelSize(14); f.setBold(True); cn_label.setFont(f)
            cn_label.setWordWrap(True)
            cn_label.setStyleSheet("color: #7C3AED; background: transparent;")
            layout.addWidget(cn_label)

        # ── 英文释义 ──
        en_def = word_data.get("definition_en", "")
        if en_def:
            en_label = QLabel(f"English: {en_def}")
            f = QFont(); f.setPixelSize(12); en_label.setFont(f)
            en_label.setWordWrap(True)
            en_label.setStyleSheet("color: #6B7280; background: transparent;")
            layout.addWidget(en_label)

        # ── 例句 ──
        sentences = word_data.get("sentences", [])
        if sentences:
            sent_label = QLabel("例句：")
            f = QFont(); f.setPixelSize(12); f.setBold(True); sent_label.setFont(f)
            sent_label.setStyleSheet("color: #374151; background: transparent;")
            layout.addWidget(sent_label)

            for s in sentences[:3]:
                if isinstance(s, dict):
                    en = s.get("sContent", "")
                    cn = s.get("sCn", "")
                    sent_text = f"📝 {en}\n   {cn}"
                else:
                    sent_text = str(s)
                sl = QLabel(sent_text)
                f = QFont(); f.setPixelSize(11); sl.setFont(f)
                sl.setWordWrap(True)
                sl.setStyleSheet("color: #4B5563; background: #F9FAFB; "
                                "border-radius: 6px; padding: 6px 8px;")
                layout.addWidget(sl)

        # ── 短语搭配 ──
        phrases = word_data.get("phrases", [])
        if phrases:
            ph_label = QLabel("短语搭配：")
            f = QFont(); f.setPixelSize(12); f.setBold(True); ph_label.setFont(f)
            ph_label.setStyleSheet("color: #374151; background: transparent;")
            layout.addWidget(ph_label)

            for p in phrases[:5]:
                if isinstance(p, dict):
                    ph_text = f"• {p.get('pContent', '')} — {p.get('pCn', '')}"
                else:
                    ph_text = f"• {p}"
                pl = QLabel(ph_text)
                f = QFont(); f.setPixelSize(11); pl.setFont(f)
                pl.setWordWrap(True)
                pl.setStyleSheet("color: #4B5563; background: transparent;")
                layout.addWidget(pl)

        layout.addStretch()

        # ── 状态 + 按钮 ──
        # 检查该词是否已在生词本中
        existing = user_vocab_repo.get_word(word, user_id)
        if existing:
            count = existing.get("lookup_count", 1)
            state = existing.get("state", "NEW")
            state_names = {"NEW": "新词", "LEARNING": "复习中", "MASTERED": "已掌握"}
            state_cn = state_names.get(state, state)
            self.status_label = QLabel(f"已在生词本中（{state_cn}，查过 {count} 次）")
            f = QFont(); f.setPixelSize(11); self.status_label.setFont(f)
            self.status_label.setStyleSheet("color: #22C55E; background: transparent; font-weight: bold;")
            layout.addWidget(self.status_label)

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            # 仍可以再加一次（增加 lookup_count）
            add_btn = QPushButton("再次加入")
            add_btn.clicked.connect(self._on_add)
            add_btn.setStyleSheet("""
                QPushButton {
                    background: #EDE9FE; color: #7C3AED; border: 2px solid #7C3AED;
                    border-radius: 10px; padding: 8px 20px; font-size: 13px; font-weight: bold;
                }
                QPushButton:hover { background: #DDD6FE; }
            """)
            btn_layout.addWidget(add_btn)
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(self.accept)
            close_btn.setStyleSheet("""
                QPushButton {
                    background: #7C3AED; color: white; border: none;
                    border-radius: 10px; padding: 8px 24px; font-size: 13px; font-weight: bold;
                }
                QPushButton:hover { background: #6D28D9; }
            """)
            btn_layout.addWidget(close_btn)
            layout.addLayout(btn_layout)
        else:
            # 词不在生词本 → 让用户决定
            self.status_label = QLabel("")
            f = QFont(); f.setPixelSize(11); self.status_label.setFont(f)
            self.status_label.setStyleSheet("color: #9CA3AF; background: transparent;")
            layout.addWidget(self.status_label)

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(self.reject)
            close_btn.setStyleSheet("""
                QPushButton {
                    background: #F3F4F6; color: #6B7280; border: none;
                    border-radius: 10px; padding: 8px 24px; font-size: 13px;
                }
                QPushButton:hover { background: #E5E7EB; }
            """)
            btn_layout.addWidget(close_btn)
            add_btn = QPushButton("加入生词本")
            add_btn.clicked.connect(self._on_add)
            add_btn.setStyleSheet("""
                QPushButton {
                    background: #7C3AED; color: white; border: none;
                    border-radius: 10px; padding: 8px 24px; font-size: 13px; font-weight: bold;
                }
                QPushButton:hover { background: #6D28D9; }
            """)
            btn_layout.addWidget(add_btn)
            layout.addLayout(btn_layout)

    def _on_add(self):
        """用户点击加入生词本。"""
        self._user_vocab_repo.upsert_lookup(
            word=self._word,
            user_id=self._user_id,
            session_id=self._session_id,
        )
        self._added = True
        self.word_saved.emit(self._word)
        existing = self._user_vocab_repo.get_word(self._word, self._user_id)
        count = existing.get("lookup_count", 1) if existing else 1
        self.status_label.setText(f"✓ 已加入生词本（查过 {count} 次）")
        self.status_label.setStyleSheet("color: #22C55E; background: transparent; font-weight: bold;")
        # 禁用加入按钮防重复点击
        btn = self.sender()
        if btn:
            btn.setEnabled(False)
            btn.setText("已加入")

    def was_added(self) -> bool:
        """返回本次弹窗是否加入了生词。"""
        return self._added

    def _lookup(self, word: str, vocab_repo, llm=None) -> dict:
        """查词：本地词典 → LLM兜底。"""
        # 1. 本地词典
        try:
            db_word = vocab_repo.get_word(word)
            if db_word:
                return {
                    "phonetic": db_word.phonetic,
                    "pos": db_word.part_of_speech,
                    "definition_cn": db_word.definition_cn,
                    "definition_en": db_word.definition_en,
                    "sentences": db_word.sentences,
                    "phrases": db_word.collocations,
                }
        except Exception:
            pass

        # 2. CloudLLM 兜底
        if llm:
            try:
                resp = llm.chat(
                    system_prompt="You are a dictionary. Explain the given word concisely.",
                    messages=[{"role": "user", "content": f"""Define the English word "{word}".
Return ONLY a JSON:
{{
  "phonetic": "/.../",
  "pos": "n./v./adj./adv.",
  "definition_cn": "Chinese definition",
  "definition_en": "English definition",
  "sentences": [{{"sContent": "Example in English", "sCn": "Chinese translation"}}]
}}
If the word doesn't exist, return {{}}. Do NOT include any other text."""}],
                )
                if resp and resp.text:
                    import json
                    text = resp.text.strip()
                    if text.startswith("```"):
                        text = text.split("\n", 1)[1]
                        if text.endswith("```"):
                            text = text[:-3]
                    data = json.loads(text)
                    if data and data.get("definition_cn"):
                        return {
                            "phonetic": data.get("phonetic", ""),
                            "pos": data.get("pos", ""),
                            "definition_cn": data.get("definition_cn", ""),
                            "definition_en": data.get("definition_en", ""),
                            "sentences": data.get("sentences", []),
                            "phrases": [],
                        }
            except Exception:
                pass

        # 3. 完全没找到
        return {
            "phonetic": "",
            "pos": "",
            "definition_cn": "释义暂不可用",
            "definition_en": "Definition not available",
            "sentences": [],
            "phrases": [],
        }
