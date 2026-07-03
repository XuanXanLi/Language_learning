"""AudioPlayer — PCM 音频播放器。

用法：
    player = AudioPlayer()
    player.play(pcm_bytes)   # 立即返回，后台线程播放
    player.stop()            # 打断当前播放

播放格式：16kHz, 16bit, mono PCM

注：PyAudio 在 play() 时才导入，模块本身不需要预装 pyaudio。
"""

import threading
from PyQt5.QtCore import QObject, pyqtSignal


class AudioPlayer(QObject):
    """播放 PCM 音频。

    play() 启动后台播放线程并立即返回，不阻塞调用线程。
    stop() 打断播放，播放线程立即退出。
    """

    playback_started = pyqtSignal()
    playback_finished = pyqtSignal()
    playback_error = pyqtSignal(str)

    CHUNK = 1024
    CHANNELS = 1
    RATE = 16000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playing = False
        self._thread: threading.Thread | None = None

    def play(self, audio_bytes: bytes):
        """开始 PCM 播放。启动后台线程，立即返回。"""
        if not audio_bytes:
            self.playback_finished.emit()
            return

        # 打断正在播放的音频
        self.stop()

        self._playing = True
        self._thread = threading.Thread(
            target=self._play_thread, args=(audio_bytes,), daemon=True
        )
        self._thread.start()

    def _play_thread(self, audio_bytes: bytes):
        """后台线程：打开 PyAudio 并逐块写入音频数据。"""
        import pyaudio

        p = None
        stream = None

        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK,
            )
            self.playback_started.emit()

            offset = 0
            chunk_bytes = self.CHUNK * 2  # 每个样本 2 字节
            while offset < len(audio_bytes) and self._playing:
                end = min(offset + chunk_bytes, len(audio_bytes))
                stream.write(audio_bytes[offset:end])
                offset = end

        except Exception as e:
            self.playback_error.emit(f"播放错误: {e}")
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p is not None:
                try:
                    p.terminate()
                except Exception:
                    pass

        self._playing = False
        self.playback_finished.emit()

    def stop(self):
        """立即打断播放。"""
        self._playing = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def is_playing(self) -> bool:
        """是否正在播放。"""
        return self._playing

    def close(self):
        """释放资源。"""
        self.stop()
