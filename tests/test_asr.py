"""ASR 模块测试 — BaseASR 抽象接口 + MockASR 实现。"""

import pytest
from line_c.asr.base import ASRResponse, BaseASR
from line_c.asr.mock_asr import MockASR


class TestASRResponse:
    """ASRResponse 数据类测试。"""

    def test_defaults(self):
        r = ASRResponse(text="hello")
        assert r.text == "hello"
        assert r.latency_ms == 0.0
        assert r.language == "auto"
        assert r.confidence == 0.0

    def test_full_fields(self):
        r = ASRResponse(text="你好", latency_ms=150.0, language="zh", confidence=0.95)
        assert r.text == "你好"
        assert r.latency_ms == 150.0
        assert r.language == "zh"
        assert r.confidence == 0.95


class TestMockASR:
    """MockASR 实现测试。"""

    def test_default_text(self):
        asr = MockASR()
        result = asr.transcribe(b"fake audio")
        assert result.text == "Hello, I want to practice English."
        assert result.latency_ms == 50.0
        assert result.language == "en"
        assert result.confidence == 0.99

    def test_custom_text(self):
        asr = MockASR(fixed_text="What is your name?")
        result = asr.transcribe(b"anything")
        assert result.text == "What is your name?"

    def test_transcribe_ignores_input(self):
        """MockASR 忽略输入音频，始终返回固定文本。"""
        asr = MockASR(fixed_text="hello")
        assert asr.transcribe(b"").text == "hello"
        assert asr.transcribe(b"\x00" * 1000).text == "hello"

    def test_call_count(self):
        asr = MockASR()
        assert asr.call_count == 0
        asr.transcribe(b"a")
        assert asr.call_count == 1
        asr.transcribe(b"b")
        asr.transcribe(b"c")
        assert asr.call_count == 3

    def test_is_available(self):
        asr = MockASR()
        assert asr.is_available() is True

    def test_name(self):
        asr = MockASR()
        assert asr.name == "MockASR"

    def test_is_base_asr(self):
        """MockASR 是 BaseASR 的子类。"""
        asr = MockASR()
        assert isinstance(asr, BaseASR)


class TestBaseASRCannotInstantiate:
    """BaseASR 是抽象类，不能直接实例化。"""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseASR()  # type: ignore[abstract]
