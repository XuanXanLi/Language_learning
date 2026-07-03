"""首页 — 角色选择与创建。

- 角色卡片列表（横向排列，最多5个）
- 新建角色：水平气泡 + 兴趣多选
- 编辑/删除：长按（右键）角色卡片
"""

import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QLineEdit, QButtonGroup, QCheckBox, QScrollArea,
    QMessageBox, QSizePolicy, QGridLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from ..chat_bubble import ChatBubble  # reuse TypingIndicator import pattern


# ── 兴趣选项 ──
INTEREST_OPTIONS = [
    ("ai_tech", "AI科技"),
    ("finance", "金融财经"),
    ("science", "科学知识"),
    ("history", "历史文化"),
    ("travel", "旅游美食"),
    ("music", "音乐影视"),
    ("sports", "体育运动"),
    ("games", "游戏动漫"),
]

LEVEL_OPTIONS = [
    ("beginner", "零基础"),
    ("primary", "初级"),
    ("middle", "中级"),
    ("high", "高级"),
    ("advanced", "流利"),
]

MAX_CHARACTERS = 5


class _CharacterCard(QWidget):
    """单个角色卡片。"""

    clicked = pyqtSignal(int)       # 点击：进入
    edit_requested = pyqtSignal(int)   # 右键：编辑
    delete_requested = pyqtSignal(int)  # 右键 → 删除

    def __init__(self, user_id: int, name: str, level: str, interests: list, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setFixedSize(160, 180)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            _CharacterCard {
                background: white;
                border-radius: 16px;
                border: 2px solid rgba(124, 58, 237, 30);
            }
            _CharacterCard:hover {
                border-color: #7C3AED;
                background: #F5F3FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)

        # 头像占位
        avatar = QLabel(name[0].upper() if name else "?")
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignCenter)
        f = QFont(); f.setPixelSize(20); f.setBold(True); avatar.setFont(f)
        avatar.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7C3AED, stop:1 #A855F7);
                color: white;
                border-radius: 24px;
            }
        """)
        layout.addWidget(avatar, alignment=Qt.AlignCenter)

        # 名字
        name_label = QLabel(name)
        f = QFont(); f.setPixelSize(15); f.setBold(True); name_label.setFont(f)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #1F2937; background: transparent;")
        layout.addWidget(name_label)

        # 水平标签
        level_names = dict(LEVEL_OPTIONS)
        lvl_label = QLabel(level_names.get(level, level))
        f = QFont(); f.setPixelSize(11); lvl_label.setFont(f)
        lvl_label.setAlignment(Qt.AlignCenter)
        lvl_label.setStyleSheet("color: #7C3AED; background: transparent; font-weight: bold;")
        layout.addWidget(lvl_label)

        # 兴趣标签
        if interests:
            interest_names = dict(INTEREST_OPTIONS)
            tags = ", ".join(interest_names.get(i, i) for i in interests[:3])
            tag_label = QLabel(tags)
            f = QFont(); f.setPixelSize(10); tag_label.setFont(f)
            tag_label.setAlignment(Qt.AlignCenter)
            tag_label.setWordWrap(True)
            tag_label.setStyleSheet("color: #6B7280; background: transparent;")
            layout.addWidget(tag_label)

        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.user_id)
        elif event.button() == Qt.RightButton:
            self.edit_requested.emit(self.user_id)
        super().mousePressEvent(event)


class _CreateCard(QWidget):
    """"+ 新建角色"卡片。"""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 180)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            _CreateCard {
                background: white;
                border-radius: 16px;
                border: 2px dashed #D1D5DB;
            }
            _CreateCard:hover {
                border-color: #7C3AED;
                background: #F5F3FF;
            }
        """)

        layout = QVBoxLayout(self)
        plus_label = QLabel("+")
        f = QFont(); f.setPixelSize(36); f.setBold(False); plus_label.setFont(f)
        plus_label.setAlignment(Qt.AlignCenter)
        plus_label.setStyleSheet("color: #D1D5DB; background: transparent;")
        layout.addWidget(plus_label)

        text = QLabel("新建角色")
        f = QFont(); f.setPixelSize(13); text.setFont(f)
        text.setAlignment(Qt.AlignCenter)
        text.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _CreateDialog(QDialog):
    """新建/编辑角色弹窗。"""

    def __init__(self, parent=None, edit_profile=None):
        super().__init__(parent)
        self.edit_profile = edit_profile
        is_edit = edit_profile is not None

        self.setWindowTitle("编辑角色" if is_edit else "创建新角色")
        self.setFixedSize(420, 480)
        self.setStyleSheet("""
            QDialog {
                background: white;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 名字
        layout.addWidget(QLabel("名字"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入角色名...")
        self.name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E5E7EB; border-radius: 8px;
                padding: 8px 12px; font-size: 14px;
            }
            QLineEdit:focus { border-color: #7C3AED; }
        """)
        layout.addWidget(self.name_input)

        # 英语水平
        layout.addWidget(QLabel("我的英语水平"))
        self.level_group = QButtonGroup(self)
        level_layout = QHBoxLayout()
        level_layout.setSpacing(6)
        for value, label in LEVEL_OPTIONS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: #F3F4F6; border: 2px solid #E5E7EB;
                    border-radius: 12px; padding: 6px 10px; font-size: 12px;
                }
                QPushButton:checked {
                    background: #EDE9FE; border-color: #7C3AED; color: #7C3AED;
                    font-weight: bold;
                }
            """)
            self.level_group.addButton(btn)
            btn.setProperty("level_value", value)
            level_layout.addWidget(btn)
        level_layout.addStretch()
        layout.addLayout(level_layout)

        # 兴趣
        layout.addWidget(QLabel("我的兴趣（多选）"))
        self.interest_checks = {}
        interest_grid = QGridLayout()
        interest_grid.setSpacing(6)
        for i, (value, label) in enumerate(INTEREST_OPTIONS):
            cb = QCheckBox(label)
            cb.setStyleSheet("""
                QCheckBox {
                    font-size: 12px; spacing: 4px;
                }
                QCheckBox::indicator {
                    width: 16px; height: 16px; border-radius: 4px;
                    border: 2px solid #D1D5DB;
                }
                QCheckBox::indicator:checked {
                    background: #7C3AED; border-color: #7C3AED;
                }
            """)
            cb.setProperty("interest_value", value)
            self.interest_checks[value] = cb
            interest_grid.addWidget(cb, i // 4, i % 4)
        layout.addLayout(interest_grid)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6; border: none; border-radius: 10px;
                padding: 8px 20px; font-size: 14px;
            }
        """)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存" if is_edit else "创建")
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7C3AED, stop:1 #A855F7);
                color: white; border: none; border-radius: 10px;
                padding: 8px 24px; font-size: 14px; font-weight: bold;
            }
        """)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        # 编辑模式：预填数据
        if edit_profile:
            self.name_input.setText(edit_profile.name)
            for btn in self.level_group.buttons():
                if btn.property("level_value") == edit_profile.english_level:
                    btn.setChecked(True)
                    break
            for interest in edit_profile.interests:
                if interest in self.interest_checks:
                    self.interest_checks[interest].setChecked(True)

        self._result = None

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            return  # 名字必填

        checked_btn = self.level_group.checkedButton()
        level = checked_btn.property("level_value") if checked_btn else "middle"

        interests = [
            v for v, cb in self.interest_checks.items() if cb.isChecked()
        ]
        if not interests:
            interests = ["ai_tech"]  # 至少一个

        self._result = {"name": name, "english_level": level, "interests": interests}
        self.accept()

    def get_result(self):
        return self._result


class HomePage(QWidget):
    """首页：角色列表 + 创建入口。"""

    character_selected = pyqtSignal(int)    # user_id
    character_created = pyqtSignal(int)     # user_id
    character_updated = pyqtSignal(int)     # user_id
    character_deleted = pyqtSignal(int)     # user_id

    def __init__(self, user_repo, parent=None):
        super().__init__(parent)
        self.user_repo = user_repo

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # 标题
        title = QLabel("VocaLand")
        f = QFont(); f.setPixelSize(28); f.setBold(True); title.setFont(f)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4C1D95; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("选择一个角色开始学习")
        f = QFont(); f.setPixelSize(14); subtitle.setFont(f)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #6B7280; background: transparent;")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        # 角色卡片区域（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignCenter)
        self.cards_layout.setSpacing(16)
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll, stretch=1)

        # 底部提示
        hint = QLabel("右键角色卡片可以编辑或删除")
        f = QFont(); f.setPixelSize(11); hint.setFont(f)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(hint)

        # 初始加载
        self._refresh_list()

    def _refresh_list(self):
        """重建角色卡片列表。"""
        # 清空旧卡片
        for i in reversed(range(self.cards_layout.count())):
            item = self.cards_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        profiles = self.user_repo.get_all()

        for p in profiles:
            card = _CharacterCard(p.id, p.name, p.english_level, p.interests)
            card.clicked.connect(self.character_selected.emit)
            card.edit_requested.connect(self._on_edit)
            self.cards_layout.addWidget(card)

        # 新建卡片（未达上限）
        if len(profiles) < MAX_CHARACTERS:
            create_card = _CreateCard()
            create_card.clicked.connect(self._on_create)
            self.cards_layout.addWidget(create_card)

        self.cards_layout.addStretch()

    def _on_create(self):
        """打开新建角色弹窗。"""
        dialog = _CreateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                from line_c.domain.user_profile import UserProfile
                profile = UserProfile(
                    name=result["name"],
                    english_level=result["english_level"],
                    interests=result["interests"],
                )
                new_id = self.user_repo.create(profile)
                self._refresh_list()
                self.character_created.emit(new_id)

    def _on_edit(self, user_id: int):
        """打开编辑角色弹窗。"""
        profile = self.user_repo.get_by_id(user_id)
        if not profile:
            return

        # 自定义右键菜单：编辑 or 删除
        msg = QMessageBox(self)
        msg.setWindowTitle("管理角色")
        msg.setText(f"角色：{profile.name}")
        edit_btn = msg.addButton("编辑", QMessageBox.ActionRole)
        delete_btn = msg.addButton("删除", QMessageBox.DestructiveRole)
        msg.addButton("取消", QMessageBox.RejectRole)
        msg.exec_()

        clicked_btn = msg.clickedButton()
        if clicked_btn == edit_btn:
            dialog = _CreateDialog(self, edit_profile=profile)
            if dialog.exec_() == QDialog.Accepted:
                result = dialog.get_result()
                if result:
                    profile.name = result["name"]
                    profile.english_level = result["english_level"]
                    profile.interests = result["interests"]
                    self.user_repo.update(profile)
                    self._refresh_list()
                    self.character_updated.emit(user_id)
        elif clicked_btn == delete_btn:
            confirm = QMessageBox.question(
                self, "确认删除",
                f"删除角色「{profile.name}」将同时删除该角色的所有学习记录，不可恢复。确定删除？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if confirm == QMessageBox.Yes:
                self.user_repo.delete(user_id)
                self._refresh_list()
                self.character_deleted.emit(user_id)
