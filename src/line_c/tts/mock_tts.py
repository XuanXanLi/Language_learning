"""MockTTS：把语音输出打印到终端的假 TTS。

用于开发阶段，不实际合成音频。
让整个对话管线在 PC 上跑通，等 Line B 部署 Piper 后替换。
"""

from .base import BaseTTS, TTSResponse


class MockTTS(BaseTTS):
    """虚拟 TTS——把文本打印到终端，不生成音频。

    用法：
        tts = MockTTS(verbose=True)
        tts.speak("Hello world")  # → 终端输出 "[TTS] Hello world"
    """

    def __init__(self, verbose: bool = True):
        self._verbose = verbose
        self._call_count = 0

    def speak(self, text: str) -> TTSResponse:
        """把文本打印到终端。"""
        self._call_count += 1
        if self._verbose:
            print(f"\n[TTS #{self._call_count}] {text}")
        return TTSResponse(audio_bytes=b"", latency_ms=0.0)

    def is_available(self) -> bool:
        return True

    @property
    def call_count(self) -> int:
        return self._call_count
