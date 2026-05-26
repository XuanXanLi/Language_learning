"""IP 角色组件 — Leo 狐狸。

左栏核心：角色形象 + 光晕 + 状态动画。
- idle: 呼吸动画（缓慢上下浮动）
- listening: 脉冲波纹扩散
- thinking: 光点浮动
- speaking: 轻微摇晃 + 光点
"""

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QPoint, QEasingCurve, pyqtProperty, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QRadialGradient, QFont


# ── 配色常量（来自设计稿 CSS 变量）──
COLOR_PRIMARY_START = "#7C3AED"
COLOR_PRIMARY_END = "#A855F7"
COLOR_PRIMARY_DARK = "#6D28D9"
COLOR_SURFACE = "#FFFFFF"
COLOR_TEXT_DARK = "#1F2937"
COLOR_TEXT_MUTED = "#6B7280"


class FoxFace(QWidget):
    """纯 QPainter 绘制的卡通狐狸头像。

    不依赖 emoji 字体、不依赖图片文件——在 Linux/嵌入式 上都保证显示。
    """

    def __init__(self, size=140, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        r = min(w, h) // 2 - 6

        # ── 耳朵（两个三角形）──
        ear_color = QColor("#E87532")
        painter.setBrush(QBrush(ear_color))
        painter.setPen(Qt.NoPen)
        left_ear = [
            QPoint(cx - int(r * 0.55), cy - int(r * 0.50)),
            QPoint(cx - int(r * 0.85), cy - int(r * 1.05)),
            QPoint(cx - int(r * 0.05), cy - int(r * 0.78)),
        ]
        right_ear = [
            QPoint(cx + int(r * 0.55), cy - int(r * 0.50)),
            QPoint(cx + int(r * 0.85), cy - int(r * 1.05)),
            QPoint(cx + int(r * 0.05), cy - int(r * 0.78)),
        ]
        for ear in [left_ear, right_ear]:
            painter.drawPolygon(*ear)

        # 耳窝（浅色内耳）
        inner_color = QColor("#F5C09E")
        painter.setBrush(QBrush(inner_color))
        inner_left = [
            QPoint(cx - int(r * 0.48), cy - int(r * 0.48)),
            QPoint(cx - int(r * 0.72), cy - int(r * 0.92)),
            QPoint(cx - int(r * 0.12), cy - int(r * 0.72)),
        ]
        inner_right = [
            QPoint(cx + int(r * 0.48), cy - int(r * 0.48)),
            QPoint(cx + int(r * 0.72), cy - int(r * 0.92)),
            QPoint(cx + int(r * 0.12), cy - int(r * 0.72)),
        ]
        for ear in [inner_left, inner_right]:
            painter.drawPolygon(*ear)

        # ── 脸（大圆）──
        face_color = QColor("#F08A3E")
        painter.setBrush(QBrush(face_color))
        painter.setPen(QPen(QColor("#D4652A"), 2))
        painter.drawEllipse(QPoint(cx, cy), r, r)

        # ── 白色嘴部区域 ──
        muzzle_color = QColor("#FFF5EE")
        painter.setBrush(QBrush(muzzle_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(cx, cy + int(r * 0.18)), int(r * 0.52), int(r * 0.38))

        # ── 眼睛 ──
        eye_r = max(1, int(r * 0.105))
        eye_y = cy - int(r * 0.08)
        eye_offset = int(r * 0.28)
        painter.setBrush(QBrush(QColor("#2D1C0A")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(cx - eye_offset, eye_y), eye_r, eye_r)
        painter.drawEllipse(QPoint(cx + eye_offset, eye_y), eye_r, eye_r)

        # 眼睛高光
        highlight_r = max(1, int(eye_r * 0.4))
        painter.setBrush(QBrush(QColor("white")))
        for ex in (cx - eye_offset, cx + eye_offset):
            px = int(ex - eye_r * 0.25)
            py = eye_y - int(eye_r * 0.3)
            painter.drawEllipse(QPoint(px, py), highlight_r, highlight_r)

        # ── 鼻子 ──
        nose_color = QColor("#3B1F0B")
        painter.setBrush(QBrush(nose_color))
        painter.drawEllipse(QPoint(cx, cy + int(r * 0.06)), int(r * 0.08), int(r * 0.06))

        # ── 嘴（两条小弧线）──
        mouth_y = cy + int(r * 0.18)
        mouth_w = int(r * 0.15)
        painter.setPen(QPen(QColor("#6B3A2A"), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(cx - mouth_w, mouth_y - mouth_w, mouth_w * 2, mouth_w * 2, 0, -90 * 16)
        painter.drawArc(cx, mouth_y - mouth_w, mouth_w * 2, mouth_w * 2, 90 * 16, -90 * 16)


class _PulseOverlay(QWidget):
    """脉冲波纹叠加层 — 用 QPainter 画扩散的圆环。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rings = [0.0, 0.0, 0.0]  # 三个环的相位 (0~1)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def start(self):
        self._timer.start(50)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        for i in range(3):
            self._rings[i] += 0.012
            if self._rings[i] > 1.0:
                self._rings[i] = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2 - 20
        base_r = 50

        for phase in self._rings:
            r = base_r + phase * 55
            alpha = int(200 * (1.0 - phase))
            if alpha < 0:
                alpha = 0
            color = QColor(253, 186, 116, alpha)  # #FDBA74
            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(cx, cy), int(r), int(r))


class _SparkleOverlay(QWidget):
    """光点浮动叠加层。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dots = [
            {"x": 0.30, "y": 0.30, "phase": 0.0, "speed": 0.018},
            {"x": 0.75, "y": 0.25, "phase": 0.4, "speed": 0.022},
            {"x": 0.80, "y": 0.65, "phase": 0.2, "speed": 0.015},
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def start(self):
        self._timer.start(50)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        for d in self._dots:
            d["phase"] += d["speed"]
            if d["phase"] > 1.0:
                d["phase"] = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for d in self._dots:
            px = int(self.width() * d["x"])
            py = int(self.height() * d["y"])
            offset_y = -10 * d["phase"]
            alpha = int(100 + 155 * (1.0 - abs(d["phase"] - 0.5) * 2))
            scale = 1.0 + 0.3 * (1.0 - abs(d["phase"] - 0.5) * 2)

            r = int(4 * scale)
            color = QColor(168, 85, 247, alpha)  # #A855F7
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(px, int(py + offset_y)), r, r)


class CharacterWidget(QWidget):
    """IP 角色组件。

    管理角色状态（idle/listening/thinking/speaking）
    和对应的动画效果。

    用法：
        char_widget = CharacterWidget()
        manager.status_changed.connect(char_widget.set_status)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "idle"

        self._build_ui()
        self._build_animations()

    # ── 布局 ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(0)

        # 状态切换按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.setSpacing(6)

        self._listen_btn = QPushButton("聆听中")
        self._listen_btn.setCheckable(True)
        self._listen_btn.setChecked(False)
        self._listen_btn.clicked.connect(lambda: self.set_status("listening"))
        self._listen_btn.setCursor(Qt.PointingHandCursor)

        self._speak_btn = QPushButton("说话中")
        self._speak_btn.setCheckable(True)
        self._speak_btn.setChecked(False)
        self._speak_btn.clicked.connect(lambda: self.set_status("speaking"))
        self._speak_btn.setCursor(Qt.PointingHandCursor)

        self._idle_btn = QPushButton("空闲")
        self._idle_btn.setCheckable(True)
        self._idle_btn.setChecked(True)
        self._idle_btn.clicked.connect(lambda: self.set_status("idle"))
        self._idle_btn.setCursor(Qt.PointingHandCursor)

        for btn in [self._listen_btn, self._speak_btn, self._idle_btn]:
            f = QFont(); f.setPixelSize(11); f.setBold(True); btn.setFont(f)
            btn.setFixedHeight(28)
            self._style_state_btn(btn, False)

        btn_layout.addWidget(self._listen_btn)
        btn_layout.addWidget(self._speak_btn)
        btn_layout.addWidget(self._idle_btn)
        layout.addLayout(btn_layout)

        # 弹性空间
        layout.addStretch()

        # 角色展示区（叠加动画层）
        char_area = QWidget()
        char_area.setFixedSize(200, 200)
        char_layout = QVBoxLayout(char_area)
        char_layout.setContentsMargins(0, 0, 0, 0)

        # 脉冲波纹层
        self._pulse = _PulseOverlay(char_area)
        self._pulse.setGeometry(0, 0, 200, 200)
        self._pulse.hide()

        # 光点层
        self._sparkle = _SparkleOverlay(char_area)
        self._sparkle.setGeometry(0, 0, 200, 200)
        self._sparkle.hide()

        # 光晕背景（用 QLabel + 渐变样式模拟）
        self._halo = QLabel(char_area)
        self._halo.setFixedSize(160, 160)
        self._halo.setStyleSheet("""
            QLabel {
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 rgba(168, 85, 247, 90),
                    stop:0.6 rgba(168, 85, 247, 15),
                    stop:1 rgba(255, 255, 255, 0)
                );
                border-radius: 80px;
            }
        """)

        # 卡通狐狸头像（纯 QPainter 绘制，不依赖 emoji 字体）
        self._avatar = FoxFace(size=140, parent=char_area)

        # 名字
        self._name = QLabel("Leo")
        self._name.setAlignment(Qt.AlignCenter)
        name_font = QFont()
        name_font.setPixelSize(22)
        name_font.setBold(True)
        self._name.setFont(name_font)
        self._name.setStyleSheet("""
            color: #4C1D95;
            background: transparent;
        """)

        # 居中叠放
        char_wrapper = QWidget()
        char_wrapper_layout = QVBoxLayout(char_wrapper)
        char_wrapper_layout.setAlignment(Qt.AlignCenter)
        char_wrapper_layout.addWidget(char_area, alignment=Qt.AlignCenter)
        char_wrapper_layout.addWidget(self._name, alignment=Qt.AlignCenter)
        layout.addWidget(char_wrapper, alignment=Qt.AlignCenter)

        layout.addStretch()

        # 状态文字
        self._status_label = QLabel("在线")
        self._status_label.setAlignment(Qt.AlignCenter)
        sf = QFont(); sf.setPixelSize(12); self._status_label.setFont(sf)
        self._status_label.setStyleSheet("color: #6B7280;")
        layout.addWidget(self._status_label, alignment=Qt.AlignCenter)

    # ── 按钮样式 ──

    def _style_state_btn(self, btn, active):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 {COLOR_PRIMARY_START}, stop:1 {COLOR_PRIMARY_END});
                    color: white;
                    border: none;
                    border-radius: 14px;
                    padding: 4px 14px;
                }}
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(124, 58, 237, 20);
                    color: #6B7280;
                    border: none;
                    border-radius: 14px;
                    padding: 4px 14px;
                }
                QPushButton:hover {
                    background: rgba(124, 58, 237, 40);
                    color: #4C1D95;
                }
            """)

    # ── 动画 ──

    def _build_animations(self):
        # 呼吸动画（idle 用）—— 上下浮动
        self._breathe_anim = QPropertyAnimation(self._avatar, b"pos")
        self._breathe_anim.setDuration(3000)
        self._breathe_anim.setLoopCount(-1)  # 无限循环

        # 说话摇晃动画
        self._shake_anim = QPropertyAnimation(self._avatar, b"pos")
        self._shake_anim.setDuration(600)
        self._shake_anim.setLoopCount(-1)

        # 存储初始位置
        self._avatar_base_pos = None

    def showEvent(self, event):
        super().showEvent(event)
        if self._avatar_base_pos is None:
            self._avatar_base_pos = self._avatar.pos()
            self._setup_breathe()
            self._breathe_anim.start()

    def _setup_breathe(self):
        base = self._avatar_base_pos
        if base is None:
            return
        self._breathe_anim.setStartValue(QPoint(base.x(), base.y()))
        self._breathe_anim.setEndValue(QPoint(base.x(), base.y() - 6))
        self._breathe_anim.setEasingCurve(QEasingCurve.InOutSine)

    def _setup_shake(self):
        base = self._avatar_base_pos
        if base is None:
            return
        self._shake_anim.setStartValue(QPoint(base.x() - 3, base.y()))
        self._shake_anim.setEndValue(QPoint(base.x() + 3, base.y() - 4))
        self._shake_anim.setEasingCurve(QEasingCurve.InOutSine)

    # ── 状态切换（公开接口）──

    def set_status(self, status: str):
        """切换到指定状态。由 ConversationManager.status_changed 信号驱动。

        status: 'idle' | 'listening' | 'thinking' | 'speaking'
        """
        self._status = status

        # 停止所有动画
        self._breathe_anim.stop()
        self._shake_anim.stop()
        self._pulse.stop()
        self._sparkle.stop()

        # 更新状态按钮高亮
        self._style_state_btn(self._idle_btn, status == "idle")
        self._style_state_btn(self._listen_btn, status == "listening")
        self._style_state_btn(self._speak_btn, status in ("thinking", "speaking"))

        if status == "idle":
            self._status_label.setText("在线")
            self._setup_breathe()
            self._breathe_anim.start()

        elif status == "listening":
            self._status_label.setText("正在聆听...")
            self._setup_breathe()
            self._breathe_anim.start()
            self._pulse.start()

        elif status == "thinking":
            self._status_label.setText("思考中...")
            self._sparkle.start()
            self._setup_breathe()
            self._breathe_anim.start()

        elif status == "speaking":
            self._status_label.setText("回复中...")
            self._sparkle.start()
            self._setup_shake()
            self._shake_anim.start()

    def status(self) -> str:
        return self._status
