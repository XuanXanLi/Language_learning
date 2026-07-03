"""MockASR：返回固定文本的假语音识别。

用于开发阶段，不需要麦克风、不需要模型、零依赖。
让整条语音对话链路在 PC 上跑通。
"""

from .base import BaseASR, ASRResponse


class MockASR(BaseASR):
    """返回预设转写文本的模拟 ASR。

    用法：
        asr = MockASR(fixed_text="I want to learn English")
        result = asr.transcribe(b"fake audio bytes")
        print(result.text)  # → "I want to learn English"

    这个类让你在没有麦克风和模型的情况下，
    把整套语音→对话→语音链路跑通。相当于排练时用的提词板。
    """

    def __init__(self, fixed_text: str = "Hello, I want to practice English."):
        """
        fixed_text: 每次 transcribe() 返回的固定文本。
        """
        self._fixed_text = fixed_text
        self._call_count = 0

    def transcribe(self, audio_bytes: bytes) -> ASRResponse:
        """返回预设文本，忽略输入音频。"""
        self._call_count += 1
        return ASRResponse(
            text=self._fixed_text,
            latency_ms=50.0,       # Mock 模拟 50ms 延迟
            language="en",
            confidence=0.99,       # Mock 高置信度
        )

    def is_available(self) -> bool:
        """MockASR 永远可用。"""
        return True

    @property
    def call_count(self) -> int:
        """查看已经被调用了几次。"""
        return self._call_count
