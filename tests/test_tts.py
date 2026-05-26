from line_c.tts.base import BaseTTS, TTSResponse
from line_c.tts.mock_tts import MockTTS


class TestMockTTS:
    def test_speak_returns_response(self):
        tts = MockTTS(verbose=False)
        resp = tts.speak("Hello world")
        assert isinstance(resp, TTSResponse)
        assert resp.latency_ms == 0.0

    def test_is_always_available(self):
        tts = MockTTS()
        assert tts.is_available()

    def test_call_count_increments(self):
        tts = MockTTS(verbose=False)
        assert tts.call_count == 0
        tts.speak("one")
        tts.speak("two")
        assert tts.call_count == 2

    def test_silent_mode_no_print(self, capsys):
        tts = MockTTS(verbose=False)
        tts.speak("quiet")
        captured = capsys.readouterr()
        assert "[TTS" not in captured.out

    def test_verbose_mode_prints(self, capsys):
        tts = MockTTS(verbose=True)
        tts.speak("Hello")
        captured = capsys.readouterr()
        assert "[TTS" in captured.out
        assert "Hello" in captured.out

    def test_name_property(self):
        tts = MockTTS()
        assert tts.name == "MockTTS"

    def test_tts_response_defaults(self):
        resp = TTSResponse(audio_bytes=b"test")
        assert resp.format == "pcm"
        assert resp.latency_ms == 0.0
