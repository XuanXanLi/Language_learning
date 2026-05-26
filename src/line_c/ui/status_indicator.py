"""状态指示器组件。

显示当前对话状态：
- idle（空闲）：等待用户输入
- listening（聆听）：用户在说话
- thinking（思考中）：LLM 正在生成回复
- speaking（说话中）：正在播放 TTS 语音
"""

from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget
from PyQt5.QtCore import Qt


STATUS_DISPLAY = {
    "idle":      ("", "就绪，等待输入..."),
    "listening": ("", "正在聆听..."),
    "thinking":  ("", "思考中..."),
    "speaking":  ("", "回复中..."),
}


class StatusIndicator(QWidget):
    """显示状态图标和文字。

    通过 set_status() 切换状态。

    用法：
        indicator = StatusIndicator()
        manager.status_changed.connect(indicator.set_status)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)

        self._icon_label = QLabel("")
        self._icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel("就绪，等待输入...")
        self._text_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self._text_label)

        layout.addStretch()

    def set_status(self, status: str):
        """切换到指定状态。

        status 必须是 'idle', 'listening', 'thinking', 'speaking' 之一。
        """
        icon, text = STATUS_DISPLAY.get(status, ("", status))
        self._icon_label.setText(icon)
        self._text_label.setText(text)
