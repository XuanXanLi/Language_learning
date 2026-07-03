"""Audio 模块测试 — AudioRecorder + AudioPlayer 单元测试。"""

import pytest
from line_c.audio.recorder import AudioRecorder
from line_c.audio.player import AudioPlayer


class TestAudioRecorder:
    """AudioRecorder 单元测试。"""

    def test_initial_state(self):
        r = AudioRecorder()
        assert r.CHUNK == 1024
        assert r.CHANNELS == 1
        assert r.RATE == 16000

    def test_signals_exist(self):
        r = AudioRecorder()
        # pyqtSignal 属性存在
        assert hasattr(r, "recording_started")
        assert hasattr(r, "recording_finished")
        assert hasattr(r, "recording_error")
        assert hasattr(r, "audio_level")

    def test_stop_when_not_recording(self):
        """未录音时 stop() 不崩溃。"""
        r = AudioRecorder()
        r.stop()  # 不应抛异常

    def test_close_when_not_started(self):
        """未启动时 close() 不崩溃。"""
        r = AudioRecorder()
        r.close()  # 不应抛异常


class TestAudioPlayer:
    """AudioPlayer 单元测试。"""

    def test_initial_state(self):
        p = AudioPlayer()
        assert p.CHUNK == 1024
        assert p.CHANNELS == 1
        assert p.RATE == 16000

    def test_signals_exist(self):
        p = AudioPlayer()
        assert hasattr(p, "playback_started")
        assert hasattr(p, "playback_finished")
        assert hasattr(p, "playback_error")

    def test_play_empty_bytes(self):
        """空音频数据 → 立即发出 finished 信号。"""
        p = AudioPlayer()
        finished = []
        p.playback_finished.connect(lambda: finished.append(True))
        p.play(b"")
        assert len(finished) == 1

    def test_stop_when_not_playing(self):
        """未播放时 stop() 不崩溃。"""
        p = AudioPlayer()
        p.stop()  # 不应抛异常

    def test_is_playing_initial(self):
        p = AudioPlayer()
        assert p.is_playing() is False

    def test_close_when_not_started(self):
        """未启动时 close() 不崩溃。"""
        p = AudioPlayer()
        p.close()  # 不应抛异常
