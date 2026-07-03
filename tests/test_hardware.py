"""Hardware 模块测试 — GpioButton 单元测试。"""

import pytest
from line_c.hardware.gpio_button import GpioButton


class TestGpioButton:
    """GpioButton 单元测试（不需要真实 GPIO 硬件）。"""

    def test_default_config(self):
        btn = GpioButton()
        assert btn.is_available() is False  # 默认不自动启动

    def test_signals_exist(self):
        btn = GpioButton()
        assert hasattr(btn, "pressed")
        assert hasattr(btn, "released")
        assert hasattr(btn, "error")

    def test_start_nonexistent_chip(self):
        """不存在的芯片路径 → start() 不崩溃，不抛异常。"""
        btn = GpioButton(chip_path="/dev/nonexistent_gpiochip999")
        btn.start()
        assert btn.is_available() is False

    def test_stop_when_not_started(self):
        btn = GpioButton()
        btn.stop()  # 不应抛异常

    def test_stop_after_failed_start(self):
        btn = GpioButton(chip_path="/dev/nonexistent")
        btn.start()
        btn.stop()  # 不应抛异常

    def test_double_start(self):
        """重复 start() 不崩溃。"""
        btn = GpioButton(chip_path="/dev/nonexistent")
        btn.start()
        btn.start()  # 不应创建重复线程
        assert btn.is_available() is False
