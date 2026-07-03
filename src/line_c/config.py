"""全局配置文件。

所有模块从这里读取配置，修改时只改这一个文件。
"""
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 数据库文件路径（SQLite 单个文件）
DATABASE_PATH = PROJECT_ROOT / "data" / "db" / "language_learner.db"

# RSS 持久化缓存（每日拉取一次，跨天自动刷新）
RSS_CACHE_DIR = PROJECT_ROOT / "data" / "rss"
RSS_CACHE_FILE = RSS_CACHE_DIR / "feed_cache.json"

# LLM 后端选择: "mock" | "ollama" | "cloud" | "rkllm"
LLM_BACKEND = "mock"

# ASR 后端选择: "mock" | "sensevoice"
ASR_BACKEND = "mock"

# TTS 后端选择: "mock" | "piper"
TTS_BACKEND = "mock"

# 音频设备配置
AUDIO_SAMPLE_RATE = 16000    # 采样率（SenseVoiceSmall 标准输入）
AUDIO_CHANNELS = 1           # 单声道
AUDIO_CHUNK_SIZE = 1024      # 每次读取的帧数

# 云端 API 配置（选 cloud 时生效）
CLOUD_API_URL = "https://api.deepseek.com/v1/chat/completions"
CLOUD_API_KEY = ""  # 优先读环境变量，其次读 .deepseek_key 文件

# 尝试从文件读取 API key（不覆盖环境变量）
_key_file = PROJECT_ROOT / ".deepseek_key"
if not CLOUD_API_KEY and _key_file.exists():
    CLOUD_API_KEY = _key_file.read_text().strip()

# Ollama 配置（选 ollama 时生效）
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
