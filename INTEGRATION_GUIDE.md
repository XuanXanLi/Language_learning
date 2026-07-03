# VocaLand v2 — Line C 集成指南

> 写给 Line A/B 智能体的使用文档。读完本文后，你应该清楚 Line C 做了什么、怎么跑起来、以及你要对接哪些接口。

---

## 一、这是什么

**VocaLand** 是一台端侧 AI 英语学习机的应用层（Line C）代码。用户用语音（或文字）和 AI 角色 Leo 聊天，Leo 在对话中自然引入 CET-4/CET-6 单词，用户在不知不觉中学会英语词汇。

- **当前版本**：v2.1
- **测试状态**：194 个单元测试全部通过
- **开发分支**：`feature/chinese-word-focus`（已提交到 GitHub）
- **运行平台**：Linux PC（开发阶段，最终目标为飞凌 ELF2 / RK3588）

---

## 二、核心数据流（端到端链路）

```
用户输入（文字/语音）
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  ChatPage (UI) 或 ConversationManager (引擎)         │
│                                                      │
│  1. 提取中文焦点词 ────→ PromptBuilder 构建提示词      │
│  2. 调用 LLM.chat(system_prompt, messages)           │
│  3. 扫描 LLM 回复中的 CET 词汇                        │
│  4. 更新词汇状态机 + 掌握度评分                         │
│  5. 调用 TTS.speak(text) 朗读回复                    │
│  6. 发出 Qt 信号通知 UI 更新                           │
└──────────────────────────────────────────────────────┘
    │
    ▼
用户看到/听到 AI 回复 → 继续对话 → 循环
```

**关键链路**：`输入 → LLM → 词汇追踪 → TTS → 输出`。这四个步骤中，**LLM 和 TTS 是抽象接口**，Line C 目前用 Mock 实现，等 Line B 的真模型就绪后替换。

---

## 三、怎么跑起来

### 3.1 环境准备

```bash
# 1. 进入项目目录
cd /home/ros/ClaudeCode/Language_learner

# 2. 激活 Python 虚拟环境（如果还没有，先创建：python3 -m venv venv）
source venv/bin/activate

# 3. 安装依赖（只需要两个！）
pip install PyQt5==5.15.9 requests==2.31.0
```

### 3.2 启动应用

```bash
# 方式 1：Mock 模式（无需网络、无需 API key，开发调试用）
PYTHONPATH=src python src/main.py

# 方式 2：Mock + 语音模式（空格键 PTT，需要 PyAudio）
PYTHONPATH=src python src/main.py --voice

# 方式 3：Cloud 模式（需要 DeepSeek API key，真实 AI 对话）
export CLOUD_API_KEY=sk-your-key-here
PYTHONPATH=src python src/main.py --llm cloud

# 方式 4：Cloud + 语音模式（最接近真机体验）
export CLOUD_API_KEY=sk-your-key-here
PYTHONPATH=src python src/main.py --llm cloud --voice
```

### 3.3 运行测试

```bash
# 全量测试
PYTHONPATH=src pytest tests/ -v

# 预期输出：194 passed
```

### 3.4 初始化数据库

```bash
# 如果数据库为空（首次运行），导入 CET-4/CET-6 词汇数据：
python scripts/generate_seed_data.py
python scripts/import_vocabulary.py
```

---

## 四、文件结构（只看关键的）

```
src/line_c/
├── config.py              # 全局配置（路径、API URL、模型名）
├── main.py                # 入口（已提交）
│
├── llm/                   # ★ LLM 接口层 — Line B 对接点
│   ├── base.py            #   抽象基类 BaseLLM（定义 chat() 签名）
│   ├── mock_llm.py        #   Mock 实现（固定回复循环）
│   └── cloud_llm.py       #   Cloud 实现（DeepSeek HTTP API）
│
├── tts/                   # ★ TTS 接口层 — Line B 对接点
│   ├── base.py            #   抽象基类 BaseTTS（定义 speak() 签名）
│   └── mock_tts.py        #   Mock 实现（打印到终端）
│
├── asr/                   # ★ ASR 接口层 — Line B 对接点（v2.2 新增）
│   ├── base.py            #   抽象基类 BaseASR（定义 transcribe() 签名）
│   └── mock_asr.py        #   Mock 实现（返回固定文本）
│
├── audio/                 # 音频 I/O 层（v2.2 新增）
│   ├── recorder.py        #   AudioRecorder — 按键录音（PyAudio）
│   └── player.py          #   AudioPlayer — PCM 播放（PyAudio）
│
├── hardware/              # 硬件抽象层（v2.2 新增）
│   └── gpio_button.py     #   GPIOButton — 物理按键监听（libgpiod）
│
├── domain/                # 领域模型（纯数据类，无外部依赖）
│   ├── word.py            #   词汇实体
│   ├── vocabulary_state.py #  五阶段状态枚举
│   ├── learning_event.py  #   学习事件类型
│   ├── learning_record.py #   状态迁移记录
│   ├── user_profile.py    #   用户/角色
│   ├── chat_session.py    #   对话会话
│   └── user_vocabulary.py #   用户词汇状态
│
├── engine/                # 业务引擎
│   ├── vocabulary_repository.py     # 词汇库 CRUD（SQLite）
│   ├── user_repository.py           # 用户 CRUD
│   ├── chat_session_repository.py   # 会话 CRUD
│   ├── user_vocabulary_repository.py# 用户词汇 CRUD
│   ├── conversation_manager.py      # ★ 对话总控制器（学习管线核心）
│   ├── prompt_builder.py            # 提示词构建器
│   ├── state_machine.py             # 五阶段状态机
│   ├── sm2_srs.py                   # SM-2 间隔复习算法
│   ├── srs_scheduler.py             # SRS 调度器
│   ├── learning_evaluator.py        # 学习评估器
│   ├── mastery_scorer.py            # 掌握度评分器
│   ├── target_word_tracker.py       # 目标词追踪器
│   ├── review_session_manager.py    # 闪卡复习管理器
│   ├── topic_generator.py           # 话题生成器
│   ├── rss_feed_fetcher.py          # RSS 新闻抓取
│   ├── rss_cache_manager.py         # RSS 缓存管理
│   └── article_extractor.py         # 文章正文提取
│
└── ui/                    # Qt 界面层
    ├── main_window.py     #   主窗口（QStackedWidget 导航壳）
    ├── pages/             #   四个页面
    │   ├── home_page.py       # 首页（角色选择/创建）
    │   ├── topic_feed_page.py # 话题页（话题卡片 + 自定义输入）
    │   ├── chat_page.py       # 聊天页（气泡对话 + 点击取词）
    │   └── review_page.py     # 复习页（闪卡翻转 + SM-2 自评）
    └── widgets/           #   可复用组件
        ├── word_popup.py      # 取词弹窗
        └── topic_preview.py   # 话题预览弹窗
```

---

## 五、Line B 对接点（重要！）

### 5.1 LLM 接口 — `src/line_c/llm/base.py`

这是 Line C 调用大语言模型的唯一入口。Line B 需要提供一个类继承 `BaseLLM`，实现两个方法：

```python
class BaseLLM(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, messages: List[dict]) -> LLMResponse:
        """发送对话请求。
        system_prompt: 系统提示词（角色设定）
        messages:      对话历史 [{"role": "user", "content": "..."}, ...]
        返回: LLMResponse(text=回复文本, latency_ms=延迟毫秒, tokens_used=消耗token数)
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用。"""
        ...
```

**对接方式**：参考 `cloud_llm.py` 的实现，写一个 `rkllm_llm.py`（或其他名字），继承 `BaseLLM`，在 `chat()` 中调用 RKLLM 推理。然后在 `main.py` 的 `create_llm()` 函数里加一个分支。

**Line C 会怎么调用**：
- 每轮对话调用一次 `chat()`
- `messages` 列表最多包含最近 6 条消息
- 回复长度预期 30-150 词
- 延迟目标：< 2 秒（真实对话体验）

### 5.2 TTS 接口 — `src/line_c/tts/base.py`

```python
class BaseTTS(ABC):
    @abstractmethod
    def speak(self, text: str) -> TTSResponse:
        """文本转语音。
        text: 要朗读的纯文本
        返回: TTSResponse(audio_bytes=PCM音频数据, format="pcm", latency_ms=延迟)
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用。"""
        ...
```

**对接方式**：参考 `mock_tts.py`，写一个 `piper_tts.py`（或 `paroli_tts.py`），继承 `BaseTTS`。音频格式预期为 PCM 16kHz 16bit mono，但可以是任何格式——UI 层不直接播放，只通过这个接口获取数据。

### 5.3 ASR 接口 — `src/line_c/asr/base.py`（v2.2 新增）

```python
@dataclass
class ASRResponse:
    text: str                    # 转写文本
    latency_ms: float = 0.0      # 识别耗时（毫秒）
    language: str = "auto"       # 检测到的语言

class BaseASR(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes) -> ASRResponse:
        """将音频字节流转写为文本。
        audio_bytes: 原始 PCM 音频数据（16kHz, 16bit, mono）
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用。"""
        ...
```

**对接方式**：参考 `mock_asr.py`，写一个 `sensevoice_asr.py`，继承 `BaseASR`。音频输入固定为 16kHz 16bit mono PCM——这个格式由 `AudioRecorder` 保证，Line B 不需要关心音频采集。

**sherpa-onnx API 参考**（SenseVoiceSmall 的实际调用方式）：
```python
import sherpa_onnx
import numpy as np

recognizer = sherpa_onnx.OfflineRecognizer(
    sherpa_onnx.OfflineRecognizerConfig(
        model=sherpa_onnx.OfflineModelConfig(
            sense_voice=sherpa_onnx.OfflineSenseVoiceModelConfig(
                model="/path/to/model.int8.onnx",
            ),
        ),
    ),
)
# PCM int16 → float32
samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
stream = recognizer.create_stream()
stream.accept_waveform(sample_rate=16000, samples=samples)
recognizer.decode_stream(stream)
text = stream.result.text
```

### 5.4 什么时候需要替换 Mock

| 组件 | Mock 行为 | 替换时机 |
|------|----------|---------|
| `MockLLM` | 返回 5 条固定英文回复，循环使用 | Line B 的 Qwen2.5-1.5B 在 RK3588 上跑通后 |
| `MockTTS` | 把文本打印到终端，不生成音频 | Line B 的 Piper/Paroli TTS 在 RK3588 上跑通后 |
| `MockASR` | 返回固定文本 "Hello, I want to practice English." | Line B 的 SenseVoiceSmall 在 RK3588 上跑通后 |

**替换步骤**：
1. 在 `src/line_c/llm/` 下新建文件，实现 `BaseLLM`
2. 在 `src/main.py` 的 `create_llm()` 中加 `--llm rkllm` 分支
3. 同理处理 TTS 和 ASR
4. 跑 `pytest tests/ -q` 确认 194 passed
5. 启动应用测试真实对话

### 5.5 语音管线（v2.2 新增）

**完整数据流**：

```
[物理按键/空格键] → AudioRecorder(后台线程) → PCM音频
    → ASR.transcribe() → 识别文本
    → 自动填入输入框 → 自动发送
    → LLM.chat()(后台线程) → AI回复文本
    → TTS.speak() → PCM音频 → AudioPlayer(后台线程) → 扬声器
```

**启动命令**：

```bash
# PC 开发（空格键 PTT）
PYTHONPATH=src python src/main.py --voice

# ELF2 + GPIO 物理按键
PYTHONPATH=src python src/main.py --voice --llm cloud \
    --gpio-chip /dev/gpiochip0 --gpio-line 17

# ELF2 + 真实模型（Line B 就绪后）
PYTHONPATH=src python src/main.py --voice \
    --llm rkllm --asr sensevoice --tts piper \
    --gpio-chip /dev/gpiochip0 --gpio-line 17
```

**GPIO 物理按键接线**（ELF2 40Pin 头）：

```
GPIO 引脚 → 10kΩ 上拉电阻 → 3.3V (Pin 1)
         └→ 按钮 → GND (Pin 6)
```

按下列表 LOW，松开高 HIGH。GPIO 引脚必须是 3.3V 电平（不能用 5V）。在 ELF2 上先用 `gpiodetect && gpioinfo` 确认可用的 chip 和 line 编号。

**架构设计**：
- `AudioRecorder` 和 `AudioPlayer` 内部使用 `threading.Thread`，不阻塞 Qt 主线程
- `_LlmWorker` 运行在 QThread 上，LLM 调用不冻结 UI
- ASR 转写结果通过 `pyqtSignal` 跨线程传回主线程
- 用户可以随时打断 TTS 播放（按键 → 停止播放 → 开始录音）

---

## 六、数据库结构

当前使用 SQLite 单文件（`data/db/language_learner.db`），包含 6 张表：

| 表名 | 用途 | 行数（当前） |
|------|------|------------|
| `words` | CET-4/CET-6 词汇库（词、释义、例句、音标、难度、状态） | ~10,000 |
| `word_mastery` | 每个词的掌握度追踪（分值、计数、最后复习时间） | 按学习进度增长 |
| `learning_events` | 每个学习事件的记录（类型、质量分、时间戳） | 按使用增长 |
| `user_profile` | 角色信息（名字、英语水平、兴趣标签） | 用户创建 |
| `chat_session` | 对话会话记录（话题、开始/结束时间） | 每次对话一条 |
| `user_vocabulary` | 用户词汇状态（NEW / LEARNING / MASTERED） | 按学习进度增长 |

**注意**：数据库文件在 `data/db/` 目录，这个目录不在 git 中（被 gitignore），需要在首次运行时创建。

---

## 七、词汇状态机（五阶段）

Line C 的核心学习逻辑围绕这个词的生命周期展开：

```
UNKNOWN ──→ INTRODUCED ──→ ATTEMPTED ──→ LEARNING ──→ MASTERED
 (未知)     (AI介绍过)     (用户用过)    (SRS排期中)   (已掌握)
```

- **UNKNOWN → INTRODUCED**：AI 在对话中自然引入该词
- **INTRODUCED → ATTEMPTED**：用户在后续对话中主动使用该词
- **ATTEMPTED → LEARNING**：使用 ≥ 2 次后进入 SM-2 间隔复习队列
- **LEARNING → MASTERED**：SM-2 算法判定掌握（连续多次高分通过）
- 任何阶段可回退（用户用错了会降级）

---

## 八、UI 导航流（用户视角）

```
首页（选角色）
  │
  ├─ 创建新角色（名字 + 英语水平 + 兴趣标签）
  │
  ▼
话题页（选话题）
  │
  ├─ RSS 新闻话题卡片（8 类 18 个中文源）
  ├─ 自定义话题输入
  ├─ 进入复习模式
  │
  ▼
聊天页（两栏）
  │
  ├─ 左：对话气泡 + 输入框
  │    └─ 点击气泡中的单词 → 弹出释义弹窗 → 加入生词本
  ├─ 右：本次会话生词面板
  │
  ▼
复习页（闪卡）
  └─ 正面（英文）→ 翻转（中文 + 例句）→ 自评（Again / Hard / Good）
```

---

## 九、关键配置（`src/line_c/config.py`）

```python
# 数据库路径
DATABASE_PATH = "data/db/language_learner.db"

# LLM 后端
LLM_BACKEND = "mock"              # "mock" | "ollama" | "cloud" | "rkllm"

# 云端 API（--llm cloud 时生效）
CLOUD_API_URL = "https://api.deepseek.com/v1/chat/completions"
CLOUD_API_KEY = ""                # 优先读环境变量 CLOUD_API_KEY

# Ollama（本地推理备选，--llm ollama 时生效）
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:1.5b"
```

---

## 十、当前开发边界（已知待完善项）

这些是 Line C 已知还没做/没做完的部分，**不影响你对接 LLM/TTS 接口**：

1. **ChatPage 未接入 ConversationManager**：聊天页目前直接调 LLM，没走学习事件管线。这意味着聊天时的词汇追踪和评估还不完整。这部分逻辑在 `conversation_manager.py` 中已经写好并通过测试，只是还没接入 UI。

2. **音标数据未在 UI 展示**：数据库里有音标字段，但取词弹窗和复习卡片没显示。

3. **学习报告 UI 未做**：学习数据都在数据库里，但还没有独立的报告页面。

4. **触屏未在真机验证**：`mousePressEvent` 理论上同时响应鼠标和触屏，但没在 ELF2 的 7 寸屏上测过。

5. **SRS 持久化未完成**：复习队列目前在会话内管理，重启后复习计划可能丢失。

---

## 十一、快速验证清单

在 ELF2 真机上验证前，先在 PC 上确认：

- [ ] `PYTHONPATH=src pytest tests/ -q` → 194 passed
- [ ] `PYTHONPATH=src python src/main.py` → GUI 窗口出现，四个页面可切换
- [ ] 首页可以创建角色（输入名字、选英语水平、选兴趣标签）
- [ ] 话题页有话题卡片（Mock 模式用规则过滤，有预设话题）
- [ ] 聊天页可以发消息、收回复、点击单词弹释义
- [ ] 复习页可以翻卡、自评

### PC 语音验证（v2.2 新增）

- [ ] `PYTHONPATH=src python src/main.py --voice` → 麦克风按钮出现在发送按钮旁边
- [ ] 空格键 / 点击麦克风 → 状态变为"录音中" → 松开 → MockASR 文本自动填入 → 自动发送
- [ ] LLM 回复时 UI 不冻结（LLM 在后台线程运行）
- [ ] MockTTS 输出在终端可见

在 ELF2 上验证（Line B 模型就绪后）：

- [ ] 用 `--llm rkllm` 启动，确认 LLM 推理正常
- [ ] TTS 替换后，确认语音输出正常
- [ ] ASR 替换后，确认语音转文字正常
- [ ] `--gpio-chip /dev/gpiochip0 --gpio-line N` 物理按键 → 完整语音对话闭环
- [ ] 完整对话 5 轮以上，无内存溢出
- [ ] 对话结束后，`data/db/language_learner.db` 中有新的学习记录

---

## 十二、常见问题

**Q: 数据库文件不存在怎么办？**
运行 `python scripts/generate_seed_data.py && python scripts/import_vocabulary.py` 生成并导入词汇数据。

**Q: 没有图形界面怎么测试？**
可以用 `python scripts/demo_engine.py` 在终端里跑引擎逻辑，不需要 Qt。

**Q: 怎么切换 LLM 后端？**
修改 `config.py` 中的 `LLM_BACKEND`，或命令行 `--llm mock|cloud`。新增后端需要在 `main.py` 的 `create_llm()` 中加分支。

**Q: `conversation_manager.py` 和 `chat_page.py` 是什么关系？**
`ConversationManager` 是 v1.0 的学习管线核心（有完整的词汇追踪、状态机、评估链路），通过 Qt 信号通知 UI。`ChatPage` 是 v2.0 的新 UI，目前直接调 LLM（简化版）。后续需要把两者接起来——这是 Line C 的下一步工作。

---

*文档生成时间：2026-07-04*
*基于分支：`feature/chinese-word-focus`*
*提交：`d2a6915` (v2.1) + `8435a41` (v2.0)*
