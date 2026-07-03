"""GPIO 物理按键监听 — 使用 libgpiod 边缘检测。

运行在后台线程中，通过 pyqtSignal 通知主线程按键事件。

用法：
    btn = GpioButton(chip_path="/dev/gpiochip0", line_num=17)
    btn.pressed.connect(on_pressed)
    btn.released.connect(on_released)
    btn.start()   # 后台线程开始监听

接线（ELF2 40Pin 头）：
    GPIO 引脚 → 10kΩ 上拉电阻到 3.3V → 按键 → GND
    未按时：HIGH (1)，按下时：LOW (0)
    软件去抖 50ms

PC 开发：如果没有 GPIO 硬件，start() 会静默跳过，
通过 GpioButton.is_available() 检查是否可用。
"""

import threading
from PyQt5.QtCore import QObject, pyqtSignal

# GPIO 默认配置（ELF2 上通过 gpiodetect 确认实际值）
DEFAULT_CHIP_PATH = "/dev/gpiochip0"
DEFAULT_LINE_NUM = 17
DEBOUNCE_SEC = 0.05   # 50ms 硬件去抖


class GpioButton(QObject):
    """监听单个 GPIO 引脚的物理按键。

    按键按下 → pressed 信号（FALLING edge）
    按键释放 → released 信号（RISING edge）
    """

    pressed = pyqtSignal()
    released = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        chip_path: str = DEFAULT_CHIP_PATH,
        line_num: int = DEFAULT_LINE_NUM,
        parent=None,
    ):
        super().__init__(parent)
        self._chip_path = chip_path
        self._line_num = line_num
        self._running = False
        self._thread: threading.Thread | None = None
        self._available = False

    def start(self):
        """启动后台 GPIO 监听线程。

        如果没有 GPIO 硬件（PC 开发环境），静默跳过，
        不崩溃、不报错。通过 is_available() 检查状态。
        """
        if self._running:
            return

        # 检查 GPIO 芯片是否可访问（PC 上没有则跳过）
        import os
        if not os.path.exists(self._chip_path):
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True
        )
        self._thread.start()

    def _monitor_loop(self):
        """后台线程：阻塞等待 GPIO 边缘事件。"""
        try:
            import gpiod

            chip = gpiod.Chip(self._chip_path)
            line = chip.get_line(self._line_num)

            # 配置为输入、上拉、双沿检测
            line.request(
                consumer="vocaland-ptt",
                type=gpiod.LINE_REQ_EV_BOTH_EDGES,
                flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP,
            )
            self._available = True

            while self._running:
                # 阻塞等待（1 秒超时方便退出）
                if line.event_wait(sec=1):
                    event = line.event_read()
                    if event.type == gpiod.LineEvent.FALLING_EDGE:
                        self.pressed.emit()
                    elif event.type == gpiod.LineEvent.RISING_EDGE:
                        self.released.emit()

            line.release()
            chip.close()
        except ImportError:
            # PC 上没有 gpiod 包，静默跳过
            pass
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._available = False

    def stop(self):
        """停止 GPIO 监听。"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_available(self) -> bool:
        """GPIO 按键是否可用（已打开芯片并成功配置）。"""
        return self._available
