"""TTS 模块——语音合成适配器。"""

from .base import BaseTTS, TTSResponse
from .mock_tts import MockTTS

__all__ = ["BaseTTS", "TTSResponse", "MockTTS"]
