"""AudioRecorder — 按键录音器。

用法：
    recorder = AudioRecorder()
    recorder.recording_finished.connect(on_finished)
    recorder.start()    # 立即返回，后台线程录音
    recorder.stop()     # 设置停止标志，线程退出时发信号

录音格式：16kHz, 16bit, mono PCM

注：PyAudio 在 start() 时才导入，模块本身不需要预装 pyaudio。
"""

import threading
from PyQt5.QtCore import QObject, pyqtSignal


class AudioRecorder(QObject):
    """从麦克风采集音频。

    start() 启动后台录音线程并立即返回，不阻塞调用线程。
    stop() 设置停止标志，录音线程退出时通过信号返回 PCM 数据。
    """

    recording_started = pyqtSignal()
    recording_finished = pyqtSignal(bytes)   # PCM 数据，16kHz, 16bit, mono
    recording_error = pyqtSignal(str)
    audio_level = pyqtSignal(float)          # RMS 电平 0.0-100.0

    CHUNK = 1024
    CHANNELS = 1
    RATE = 16000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recording = False
        self._frames: list[bytes] = []
        self._thread: threading.Thread | None = None

    def start(self):
        """开始录音。启动后台线程，立即返回。"""
        if self._recording:
            return

        self._frames = []
        self._recording = True
        self.recording_started.emit()

        self._thread = threading.Thread(target=self._record_thread, daemon=True)
        self._thread.start()

    def _record_thread(self):
        """后台线程：打开 PyAudio 并循环读取音频帧。"""
        import pyaudio
        import math
        import struct

        p = None
        stream = None

        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

            while self._recording:
                try:
                    data = stream.read(self.CHUNK, exception_on_overflow=False)
                except Exception:
                    break
                self._frames.append(data)

                # 计算 RMS 电平
                sample_count = len(data) // 2
                if sample_count > 0:
                    samples = struct.unpack(f"<{sample_count}h", data)
                    rms = math.sqrt(sum(s * s for s in samples) / sample_count)
                    level = min(rms / 32768.0 * 100.0, 100.0)
                    self.audio_level.emit(level)

        except Exception as e:
            self.recording_error.emit(f"录音错误: {e}")
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

        # 线程退出时返回录音数据
        all_data = b"".join(self._frames)
        self._frames = []
        self._recording = False
        self.recording_finished.emit(all_data)

    def stop(self):
        """设置停止标志。录音线程会在下一次 read() 后退出。"""
        self._recording = False

    def close(self):
        """释放资源。"""
        self._recording = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
