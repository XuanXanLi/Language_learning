"""ASR 模块——语音识别适配器。"""

from .base import BaseASR, ASRResponse
from .mock_asr import MockASR

__all__ = ["BaseASR", "ASRResponse", "MockASR"]
