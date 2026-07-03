"""ASR 适配器的抽象基类。

整个项目通过这个接口调用语音识别。换 ASR 后端
（Mock → SenseVoice → Whisper）不需要改业务代码。

抽象基类（ABC, Abstract Base Class）：定义方法的签名，
但不能直接实例化。子类必须实现这些方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ASRResponse:
    """ASR 的一次转写结果。

    dataclass 自动生成 __init__，你只需要声明字段和类型。
    """
    text: str                         # 转写文本
    latency_ms: float = 0.0           # 识别耗时（毫秒）
    language: str = "auto"            # 检测到的语言 (zh/en/auto)
    confidence: float = 0.0           # 置信度 0.0-1.0


class BaseASR(ABC):
    """ASR 抽象基类——所有语音识别后端的统一接口。

    子类必须实现：
    - transcribe(): 音频字节流 → 转写文本
    - is_available(): 检查后端是否可用
    """

    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> ASRResponse:
        """将音频字节流转写为文本。

        参数：
        - audio_bytes: 原始 PCM 音频数据（16kHz, 16bit, mono）

        返回：
        - ASRResponse: 包含转写文本和元信息
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检测 ASR 后端是否可用。

        MockASR 永远返回 True，
        SenseVoiceASR 会检测模型文件是否存在、NPU 是否就绪。
        """
        ...

    @property
    def name(self) -> str:
        """后端名称，方便日志输出。"""
        return self.__class__.__name__
