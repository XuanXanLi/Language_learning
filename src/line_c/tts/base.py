"""TTS 适配器的抽象基类。

整个项目通过这个接口调用语音合成。换 TTS 后端
（Mock → Piper → MeloTTS）不需要改业务代码。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSResponse:
    """TTS 的一次合成结果。"""
    audio_bytes: bytes      # PCM 音频数据（16kHz, 16bit, mono）
    format: str = "pcm"     # 音频格式: "pcm" | "wav" | "mp3"
    latency_ms: float = 0.0


class BaseTTS(ABC):
    """TTS 抽象基类——所有 TTS 后端的统一接口。

    子类必须实现：
    - speak(): 文本转语音，返回音频数据
    - is_available(): 检查后端是否可用
    """

    @abstractmethod
    def speak(self, text: str) -> TTSResponse:
        """把文本转成语音。

        参数：text — 要朗读的纯文本（不含 SSML 等标记）

        返回：TTSResponse，包含音频字节和元信息
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检测 TTS 后端是否可用。

        MockTTS 永远返回 True，
        PiperTTS 会检测模型文件是否存在、NPU 是否就绪。
        """
        ...

    @property
    def name(self) -> str:
        """后端名称，方便日志输出。"""
        return self.__class__.__name__
