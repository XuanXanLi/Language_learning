# 开发日志：端侧AI语言学习机 (Line C)

> 记录从项目立项至今的所有实际开发步骤、技术决策及原因。
> 供后续项目流程参考和复盘。

---

## Phase 0 — 项目初始化 (2026-05)

### 决定：项目结构采用三层分层（domain / engine / ui）

**当时情况**：Line C 需要同时做词汇库、提示词、状态机、Qt 界面，如果所有代码混在一起，改一个模块可能碰坏另一个。

**方案对比**：
- A：所有代码放一个文件 → 简单但不可维护
- B：按功能分模块（domain/engine/ui）→ 多写几行导入，但每个模块职责清晰

**选择 B**。理由：
- domain（领域层）= 纯数据，不依赖 PyQt、不依赖数据库。Word、VocabularyState 这些"是什么"
- engine（引擎层）= 逻辑，依赖 domain，不依赖 UI。状态机、SRS、PromptBuilder
- ui（界面层）= 只负责画界面，通过信号/槽和 engine 沟通
- 移植到 ELF2 时，如果 Qt 版本不兼容，只需改 ui 层，domain 和 engine 完全不受影响

### 决定：用 SQLite 而非 JSON 文件存储词汇和学习记录

**当时情况**：200 个种子词，用 JSON 文件也能读写。但这套系统后续要不断查询（"这个词的状态是什么？""今天要复习哪些词？"）。

**方案对比**：
- A：JSON 文件 → 零依赖，但每次读全文件、写全文件，查询靠遍历
- B：SQLite → 需要写 SQL，但单文件存储、支持索引查询、Python 内置无需安装

**选择 B**。理由：
- JSON 在 200 词时很快，但当词库升级到 6000+ 词时，每次查询要遍历整个列表
- SQLite 的 `WHERE state = 'LEARNING'` 查询比 JSON 遍历快几十倍
- SQLite 和 JSON 一样是单文件，不需要数据库服务器，嵌入式设备友好
- 代价：需要学 SQL 语法（INSERT/SELECT/UPDATE），但这个学习成本值得

### 决定：用 Repository 模式封装数据库操作

**当时情况**：SQL 语句可以直接写在 ConversationManager 里，为什么单独建一个 VocabularyRepository 类？

**选择 Repository 模式**。理由：
- 把"怎么存数据"和"怎么用数据"分开
- 如果以后换数据库（SQLite → 其他），只改这一个文件
- 测试时可以轻松模拟（mock）Repository，不依赖真实数据库

---

## Phase 1 — C1: 词汇库构建 (2026-05)

### 决定：Word 用 Python dataclass 而非普通 dict

**方案对比**：
- A：`word = {"word": "abandon", "phonetic": "..."}` → 灵活但容易打错字（`word["phonetic"]` 写错不报错）
- B：`Word(word="abandon", phonetic="...")` → 字段有类型检查，IDE 有自动补全

**选择 B**。dataclass 自动生成 `__init__`，省手写代码，同时有编译期检查。

### 决定：学习状态五阶段模型

```
UNKNOWN → INTRODUCED → ATTEMPTED → LEARNING → MASTERED
```

**为什么不简单地用"会/不会"两个状态？** 
因为对话式学习和卡片背诵不同——一个词不是"今天学了就会了"，而是经过"见过→试过→复习中→彻底掌握"的过程。五阶段映射了真实的语言习得路径：

| 阶段 | 含义 | 触发条件 |
|------|------|----------|
| UNKNOWN | 从未见过 | 初始状态 |
| INTRODUCED | LLM 在对话中用过这个词 | 用户第一次遇到 |
| ATTEMPTED | 用户自己主动用过这个词 | 用户输出中包含 |
| LEARNING | 进入 SRS 排期复习 | 用户用了 ≥2 次 |
| MASTERED | SRS 间隔达到 30 天 | SM-2 算法判定 |

### 决定：种子数据手写 200 词

**当时情况**：先有数据才能测逻辑。200 词按话题分组（日常、情绪、教育、旅行等），每个词含音标、释义、例句、近反义词。

**这是临时方案**，后续会被 kajweb/dict 的 6600+ 词替换。但 200 词的数据结构定义了后续所有代码的数据契约。

---

## Phase 2 — C2: 提示词原型 (2026-05)

### 决定：LLM 提示词采用两层架构（系统层 + 会话层）

**参考来源**：Duolingo "Video Call with Lily" 的多阶段提示词架构。

**方案对比**：
- A：单一大提示词（把所有指令塞进一段话）→ LLM 容易发生"角色漂移"——说着说着忘了自己是老师
- B：分层提示词（系统层固定 + 会话层动态）→ 系统层始终是角色底线，会话层只放本轮相关的词

**选择 B**。理由：
- 单一大提示词把 2000 个 token 全堆在一条消息里，LLM 对"最近该用哪几个词"的注意力被稀释
- 分层后，系统 Prompt 是稳定的，会话上下文只包含最近 10 个词，LLM 更容易自然地回抛这些词
- Duolingo 是经过千万用户验证的产品，借鉴他们的架构比自己做实验快

### 决定：MockLLM 的循环回复模式

**当时情况**：真 LLM 需要网络和 API Key，写代码时不可能每次改完就等网络调用。需要一个不依赖外部的开发环境。

**方案**：MockLLM 维护一个预设回复列表，按顺序循环返回。`chat()` 调用零延迟。这个模式让"代码写完 → 跑起来看效果"的循环缩短到秒级。

### 决定：BaseLLM 抽象接口

**选择抽象基类模式**。理由：
- 和 Repository 模式同样的逻辑——隔离"用什么 LLM"和"怎么用 LLM"
- `MockLLM`（开发）和 `CloudLLM`（联网测试）和未来 `RKLLM`（真机 NPU）共用一个接口
- 在 `main.py` 里一行切换，不需要改 ConversationManager 的任何代码

### 决定：CloudLLM 后端选 DeepSeek API

**当时情况**：需要一个能用 `CLOUD_API_KEY` 调用的中文友好 LLM API。

**选择 DeepSeek**。理由：
- API 格式兼容 OpenAI，社区生态好
- 中文能力强（对话中学英语需要理解用户的汉语混用）
- 价格低
- 替代方案（OpenAI API / 通义千问）也能用，但 DeepSeek 在性价比上最优

---

## Phase 3 — C3: 状态机 + SRS 引擎 (2026-05)

### 决定：选 SM-2 算法而非更新的 SM-15/SM-18

**SM-2 vs SM-15 对比**：

| 维度 | SM-2 | SM-15 |
|------|------|-------|
| 参数个数 | 3（interval, repetition, EF） | 17+ |
| 可解释性 | 一目了然 | 需要查表格 |
| 算力需求 | 纯数学公式 | 查表 + 多维计算 |
| 效果差异 | 对 5000 词以下无明显差距 | 大规模数据更精准 |

**选择 SM-2**。理由：
- 我们的词汇量在 1 万以内，SM-2 和 SM-15 在这个量级上没有可感知的差异
- SM-2 是纯函数（输入 quality → 返回新 interval），零副作用，单元测试只需要 5 行
- 这是一个嵌入式设备，省下的算力可以给 LLM 用
- SM-2 的"1天→6天→15天→37天→91天"间隔曲线对我们场景完全够用

### 决定：SRSScheduler 不存数据库，只存内存

**当时情况**：复习调度信息需要持久化吗？应用重启后是否保留上次的复习计划？

**选择：会话内存在内存，不跨会话持久化（v1.0）**。

理由：
- 学习机是"每次开机用一会儿就关"的设备，不是 24 小时运行的后台服务
- 复习计划跨天保存需要处理"关机后时间流逝"的问题（时钟偏移、过期批量处理），第一版不必要增加复杂度
- `SRSScheduler` 用字典存储调度信息，关机即丢，开机重新 schedule
- 如果后续需要持久化，只需把内存字典序列化到 SQLite，接口（`schedule(word, quality)`）不变

### 决定：ConversationManager 用 PyQt 信号通知 UI

**当时情况**：状态变化后怎么通知界面更新？可以直接调 UI 方法，也可以用信号机制。

**选择信号（Qt Signal）**。理由：
- 信号/槽是 Qt 框架的原生机制，零依赖
- 信号解耦了"谁产生事件"和"谁关心事件"——ConversationManager 不知道 UI 怎么处理消息，只负责发射信号
- 测试友好：可以不启动 Qt 界面，只监听信号集合来验证逻辑

三个信号：
- `message_received(text, is_user)` → 新消息到达，UI 弹出气泡
- `status_changed(status)` → 状态切换，UI 更新指示灯
- `word_event(word, event, state)` → 词汇状态变化，UI 更新词汇面板

---

## Phase 4 — C4: Qt 对话界面 (2026-05)

### 决定：聊天气泡用 QLabel 而非 QTextEdit

**方案对比**：
- A：每条消息用 QTextEdit → 自动支持富文本、滚动，但渲染重
- B：每条消息用 QLabel → 轻量，`setWordWrap(True)` 足够日常文本

**选择 B**。理由：对话消息是纯文本（无富文本需求），QLabel 性能更好，EL2 上要同时跑 LLM（2.5GB 内存），UI 不能占用过多资源。

### 决定：词汇摘要面板（WordSummary）实时追踪

用户在聊天时，右下角自动更新"见过哪些词""用过哪些词""哪些进入复习""哪些是薄弱词"。这个面板不是为了"背诵"，而是让学习者意识到"原来我刚才聊天中遇到了这么多 CET 词汇"——增强学习信心。

---

## Phase 5 — 词汇数据源升级 (2026-05-22)

### 决定：从手写 200 词升级到 kajweb/dict 6600+ 词

**当时情况**：手写的 200 词数据结构完整但来源不权威、覆盖面太窄（CET-4 考纲有 4500 词）。

**搜索到的候选**：

| 数据源 | 词数 | 数据来源 | 优点 |
|--------|------|----------|------|
| kajweb/dict | CET-4 4544 + CET-6 2340 | 有道词典 API | 有音标、例句、短语、真题、同义词 |
| KyleBing/english-vocabulary | 同上 | kajweb/dict 简化版 | 更简洁 |
| kaysting/english-dictionary | 50000+ | Free Dictionary API | 通用词典 |

**选择 kajweb/dict**。理由：
- 直接按 CET-4/CET-6 组织，不需要从通用词典中筛选
- 每条数据包含有道词典 API 的发音参数，可以直接拼 URL 获取标准发音
- 真题数据（515 词含真题）对后续出题功能有用

### 决定：扩展数据库 schema 而非替换

**方案对比**：
- A：只保留 kajweb/dict 的字段，删除现有 topic_tags、difficulty 等 → 丢失我们已有的逻辑
- B：在现有 words 表增加列（us_phonetic, uk_phonetic 等），新增子表存例句和短语 → 向后兼容

**选择 B**。理由：
- 现有代码（ConversationManager、PromptBuilder）只读写 words 表的基础字段，新列不影响
- 例句和短语存子表（word_sentences、word_collocations），按需查询，不撑大主表
- 数据库从 200 词增长到 6664 词，大小只有 8.3 MB——嵌入式完全无压力
- 所有 83 个现有测试无需修改，直接通过

### 决定：多文件同名去重合并策略

CET-4 拆成 3 个 JSON 文件（CET4_1/2/3），同一词在不同文件中出现。合并时：
- 取定义最完整的为基础
- 合并所有不重复的例句和短语（按内容去重）
- 保留有真题数据的那份

这样可以最大化每词的信息量。

---

## Phase 6 — 发音纠正方案设计 (2026-05-22)

### 决定：第一版做 L1（LLM 自然示范），第二版升级 L2（音素评分）

**L1 方案**：在 PromptBuilder 中告诉 LLM "如果用户用错词，在回复中自然示范正确用法"。这是纯 Prompt 逻辑，零额外代码。

**L2 方案**：在 ASR 和 ConversationManager 之间插入一个 `PronunciationAssessor` 模块。这个模块是独立的抽象接口（和 BaseLLM 一样的模式），不影响现有代码。

**L1→L2 为什么不"推倒重来"**：因为 L1 的纠正逻辑在 Prompt 中，L2 的纠正逻辑在独立的评估器中，两者不冲突。升级时只需要加一个新组件，不需要替换旧组件。

---

## Phase 7 — TTS 方案设计 (2026-05-22)

### 决定：TTS 接口设计采用和 LLM 相同的抽象模式

创建一个 `BaseTTS` 抽象基类（定义 `speak(text) → audio` 方法的签名），具体实现可以切换：
- `MockTTS`（打印文本到终端）→ PC 开发用
- `PiperTTS`（Paroli RKNN）→ ELF2 真机用
- 未来 `MeloTTS` → 升级用

**为什么先做接口？** 因为 TTS 的具体模型（Piper）是 Line B 负责部署的，Line C 不需要等 Line B 做完——先把接口写好，ConversationManager 调用 `self.tts.speak(text)`，至于这个 `speak` 是打印到终端还是真的发出声音，是运行时决定的。

### 决定：第一版选 Piper + SSML，预留 MeloTTS 升级路径

| 方案 | 模型大小 | 自然度 | 情感 | ELF2 可运行 |
|------|----------|--------|------|:--:|
| A: Piper + SSML | 200MB | ★★☆ | 无 | 是 |
| B: MeloTTS | 500MB | ★★★ | 有 | 是 |
| C: CosyVoice2 | 3GB | ★★★★★ | 灵活 | 否（OOM） |

**选 A**。理由：唯一在 RK3588 上有社区验证的 NPU 加速方案（Paroli 项目），不会被内存问题卡住。B 是 A 的即插即用升级（换一个 `BaseTTS` 实现类），不需要改写任何业务代码。

---

## 关键决策总表

| # | 决策 | 选择 | 核心原因 |
|---|------|------|----------|
| 1 | 项目结构 | domain/engine/ui 分层 | 模块解耦，移植 ELF2 时不牵连 |
| 2 | 存储方案 | SQLite | 单文件、支持索引查询、Python 内置 |
| 3 | 数据库模式 | Repository 模式 | 隔离 SQL 细节，可替换后端 |
| 4 | 数据模型 | dataclass | 类型检查 + 自动 __init__ |
| 5 | 学习状态模型 | 五阶段状态机 | 映射真实语言习得路径 |
| 6 | 提示词架构 | 两层分层 | Duolingo 验证过的模式，避免角色漂移 |
| 7 | LLM 接口 | 抽象基类 | 一行代码切换 Mock/Cloud/RKLLM |
| 8 | Cloud 后端 | DeepSeek API | 性价比最优，中文友好 |
| 9 | 复习算法 | SM-2 | 够用，可解释，零算力开销 |
| 10 | SRS 持久化 | 内存（不跨会话） | 关机即弃，第一版够用 |
| 11 | UI 通信 | Qt 信号/槽 | 解耦 engine 和 UI，测试友好 |
| 12 | 聊天气泡 | QLabel | 轻量，嵌入式性能友好 |
| 13 | 词库数据源 | kajweb/dict | 有道词典源，CET-4/6 按级组织 |
| 14 | Schema 扩展 | 增加列 + 子表 | 向后兼容，现有代码不改 |
| 15 | 发音纠正 | L1(LLM) → 预留 L2 | L1 零代码成本，L2 独立模块不冲突 |
| 16 | TTS 接口 | 抽象基类（同 LLM 模式） | 等 Line B 部署期间即可并行开发 |
| 17 | TTS 引擎 | Piper (A) 预留 MeloTTS (B) | A 可运行，B 即插即换 |

---

# 接口参考（Interface Reference）

> 本章节供换设备、换队友、换后端时查阅。无需读源码即可理解每个接口的职责和使用方式。

---

## 一、系统全景

```
┌─────────────┐
│  main.py     │  组装所有组件，选择后端（Mock/Cloud/Piper）
└──────┬───────┘
       │ 创建并注入
       ▼
┌──────────────────────────────────────────────────────┐
│              ConversationManager                      │
│              (总控制器，唯一对外入口)                   │
│                                                      │
│  信号（给 UI 用的）：                                  │
│    message_received(text, is_user)  → 弹出气泡        │
│    status_changed(status)           → 更新状态灯      │
│    word_event(word, event, state)   → 更新词汇面板    │
│                                                      │
│  每轮对话流程：                                        │
│    handle_user_message(text)                          │
│      → _scan_message()     查词库                      │
│      → PromptBuilder       构建提示词                  │
│      → BaseLLM.chat()      获取 LLM 回复               │
│      → BaseTTS.speak()     朗读回复                    │
│      → SRSScheduler        安排复习                    │
└───┬────────────┬────────────┬────────────┬───────────┘
    │            │            │            │
    ▼            ▼            ▼            ▼
┌────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
│BaseLLM │ │BaseTTS   │ │Prompt   │ │Vocabulary│
│接口    │ │接口      │ │Builder  │ │Repository│
│        │ │          │ │         │ │          │
│MockLLM │ │MockTTS   │ │  固定   │ │ SQLite   │
│CloudLLM│ │(PiperTTS)│ │  模板   │ │          │
│(RKLLM) │ │(MeloTTS) │ │         │ │SRSSched  │
└────────┘ └──────────┘ └─────────┘ └──────────┘
```

**依赖方向**：`main.py` → `ConversationManager` → 各接口。UI 不依赖 engine，engine 不依赖 UI。

---

## 二、BaseLLM 接口 — 文本生成适配器

### 接口定义

**文件**：`src/line_c/tts/base.py`
**文件**：`src/line_c/llm/base.py`

```python
class BaseLLM(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, messages: List[dict]) -> LLMResponse:
        """发送对话请求。
        system_prompt: 角色设定文本
        messages:      [{"role": "user", "content": "..."}, ...]
        返回 LLMResponse(text, latency_ms, tokens_used)
        """

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用。MockLLM 永远 True。"""

    @property
    def name(self) -> str:
        """后端名称，日志用。"""
```

### 返回值

```python
@dataclass
class LLMResponse:
    text: str                  # 回复文本
    latency_ms: float = 0.0    # 耗时（毫秒）
    tokens_used: int = 0       # 消耗 token 数
```

### 已有实现

| 类 | 位置 | 用途 |
|----|------|------|
| `MockLLM` | `src/line_c/llm/mock_llm.py` | PC 开发，返回预设文本，零延迟 |
| `CloudLLM` | `src/line_c/llm/cloud_llm.py` | 联网调用 DeepSeek API |

### 如何新增一个 LLM 后端

1. 在 `src/line_c/llm/` 下建新文件（如 `rkllm.py`）
2. 继承 `BaseLLM`，实现 `chat()` 和 `is_available()`
3. 在 `main.py` 中 `if backend == "rkllm": return RKLLMAdapter()`

**已有代码不需要任何修改**。ConversationManager 只依赖 `BaseLLM` 接口，不依赖具体实现。

---

## 三、BaseTTS 接口 — 语音合成适配器

### 接口定义

**文件**：`src/line_c/tts/base.py`

```python
@dataclass
class TTSResponse:
    audio_bytes: bytes      # PCM 音频数据（16kHz, 16bit, mono）
    format: str = "pcm"     # "pcm" | "wav" | "mp3"
    latency_ms: float = 0.0

class BaseTTS(ABC):
    @abstractmethod
    def speak(self, text: str) -> TTSResponse:
        """文本 → 语音。同步返回音频数据。"""

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否就绪。"""

    @property
    def name(self) -> str:
        """后端名称，日志用。"""
```

### 已有实现

| 类 | 位置 | 用途 |
|----|------|------|
| `MockTTS` | `src/line_c/tts/mock_tts.py` | PC 开发，打印文本到终端 |
| `PiperTTS` | 待 Line B 实现 | ELF2 真机 NPU 加速语音合成 |

### MockTTS 行为

- `verbose=True`（默认）：每个 `speak()` 调用在终端打印 `[TTS #N] 文本内容`
- `verbose=False`：静默，什么也不输出
- `call_count` 属性：记录被调用了几次，调试用

### 如何新增 PiperTTS（Line B 完成后）

1. 新建 `src/line_c/tts/piper_tts.py`
2. 继承 `BaseTTS`，在 `speak()` 中调用 Piper 的 HTTP API
3. 在 `main.py` 中 `tts = PiperTTS(api_url="http://localhost:5002")`

**ConversationManager 和所有 UI 代码不需要修改**。

### 使用方式（在 ConversationManager 中）

```python
# 第 176-180 行
self._update_status("speaking")
if self.tts and self.tts.is_available():
    self.tts.speak(response.text)    # ← 这一行
self._update_status("idle")
```

注意：`tts` 参数是可选的（`Optional[BaseTTS] = None`），不传则跳过语音输出。

---

## 四、ConversationManager — 对话总控制器

### 职责

这是 Line C 的"总指挥"。**外部代码和 UI 只和它沟通，不直接碰其他模块。**

### 构造

```python
manager = ConversationManager(
    llm=MockLLM(),              # 必需：LLM 实例
    repository=repo,            # 必需：词汇数据库
    prompt_builder=None,        # 可选：不传用默认 PromptBuilder
    tts=None,                   # 可选：不传则不输出语音
)
```

### 公开方法

```python
# 开始新会话
manager.start_session(topic="daily life")
# topic 可选值: "daily life", "travel", "work", "food", "technology"

# 处理用户输入（核心入口，每轮对话调一次）
manager.handle_user_message("I like hiking")

# 获取会话摘要
summary = manager.get_session_summary()
# → {"topic": "travel", "turns": 5, "words_seen": [...], ...}

# 获取最近遇到的词（给 Prompt 用）
manager.get_recent_words(limit=20)  # → ["hiking", "energetic", ...]
```

### 信号（UI 监听这些）

```python
# 新消息到达 — UI 弹出气泡
manager.message_received.connect(
    lambda text, is_user: add_bubble(text, is_user)
)

# 状态变化 — UI 更新状态灯
manager.status_changed.connect(
    lambda status: update_indicator(status)
)
# status 值: "idle", "listening", "thinking", "speaking"

# 词汇事件 — UI 更新词汇面板
manager.word_event.connect(
    lambda word, event, state: on_word_update(word, event, state)
)
# event 值: "seen" (LLM 引入), "used" (用户使用),
#           "learning" (进入复习), "weak" (标记薄弱)
```

### 每轮处理流程（内部）

```
handle_user_message(text)
  1. emit message_received(text, True)     → UI 显示用户气泡
  2. _scan_message(text, "user")           → 查词库，更新状态
  3. _update_status("thinking")            → UI 显示"思考中"
  4. 加入对话历史
  5. PromptBuilder.build(...)              → 构建提示词
  6. llm.chat(...)                         → 获取 LLM 回复
  7. emit message_received(text, False)    → UI 显示 AI 气泡
  8. 加入对话历史
  9. _scan_message(text, "llm")            → 扫描 LLM 回复中的词
  10. _evaluate_progress()                 → 每 5 轮评估薄弱词
  11. tts.speak(text)                      → 语音输出
  12. _update_status("idle")               → 恢复空闲
```

---

## 五、PromptBuilder — 提示词构建器

### 职责

把角色设定 + 用户等级 + 最近遇到的词 + 薄弱词 → 拼成发给 LLM 的完整 System Prompt。

### 文件

`src/line_c/engine/prompt_builder.py`

### 用法

```python
builder = PromptBuilder(
    persona_name="Leo",         # 角色名
    cefr_level="CET-4",         # 难度等级
    vocab_size="about 2000",    # 用户词汇量
    max_words=50,               # 回复最多多少词
    preferred_topic="daily life", # 默认话题
)

# 每轮对话时调用
prompt = builder.build(
    recent_words=["hiking", "energetic", "discover"],
    weak_words=["endurance"],
    preferred_topic="travel",    # 可临时覆盖话题
)

# 会话上下文（追加在 System Prompt 后面）
ctx = builder.build_session_context(
    recent_words=["hiking", "discover"],
    turns_this_session=5,
)
```

### 提示词结构

```
[系统层 — 固定不变]
  You are Leo, a friendly English-speaking companion.
  English level: CET-4
  规则: 自然对话、纠错方式、回复长度...

[动态段 — 每轮可能变]
  ## Words Your Partner Has Recently Encountered
  hiking, energetic, discover
  (有的话就自然地回抛这些词)

  ## Words Your Partner Struggles With
  endurance
  (有机会的话用这个词)
```

### 如何定制

```python
builder = PromptBuilder(persona_name="Alice", cefr_level="CET-6")
# 或者直接改 SYSTEM_PROMPT_TEMPLATE 字符串
```

---

## 六、VocabularyRepository — 词汇数据仓库

### 职责

所有 SQL 操作集中在这里。外部代码不写 SQL，只调用 Repository 的方法。

### 文件

`src/line_c/engine/vocabulary_repository.py`

### 构造

```python
from line_c.config import DATABASE_PATH
repo = VocabularyRepository(DATABASE_PATH)
# db_path: SQLite 文件路径（不存在则自动创建）
```

### 查询方法

```python
# 单个词查询
word = repo.get_word("abandon")
# → Word 对象 或 None

# 按等级筛选（cet4 / cet6 / custom）
words = repo.get_words_by_level("cet4", limit=100)

# 按话题标签模糊搜索
words = repo.get_words_by_topic("travel", limit=20)

# 按学习状态筛选
from line_c.domain.vocabulary_state import VocabularyState
words = repo.get_words_by_state(VocabularyState.LEARNING, limit=50)

# 总词数
count = repo.word_count()
```

### 写入方法

```python
from line_c.domain.word import Word

w = Word(word="abandon", phonetic=..., part_of_speech="v.", ...)
repo.add_word(w)           # 单条插入
repo.add_words([w1, w2])   # 批量插入（快）

# 更新学习状态
repo.update_word_state("abandon", VocabularyState.LEARNING)
# → True（更新成功）或 False（词不存在）
```

### 数据库结构

**主表 `words`**：
| 列 | 类型 | 说明 |
|----|------|------|
| word | TEXT PK | 拼写 |
| phonetic | TEXT | 默认音标（英音） |
| us_phonetic / uk_phonetic | TEXT | 美/英音标 |
| us_speech / uk_speech | TEXT | 有道发音 API 参数 |
| part_of_speech | TEXT | 词性 |
| definition_en / definition_cn | TEXT | 英/中释义 |
| examples | JSON TEXT | 例句列表 |
| level | TEXT | cet4 / cet6 |
| topic_tags | JSON TEXT | 话题标签 |
| synonyms / antonyms | JSON TEXT | 近/反义词（扁平） |
| grouped_synonyms | JSON TEXT | 按词性分组的近义词 |
| exam_data | JSON TEXT | 真题（可选） |
| state | TEXT | 学习状态 |
| difficulty | REAL | 难度系数 0-1 |

**子表 `word_sentences`**：`(word, s_content, s_cn, idx)` — 例句

**子表 `word_collocations`**：`(word, p_content, p_cn)` — 短语搭配

### 发音音频获取

```python
word = repo.get_word("abandon")
# 有道词典 API URL:
uk_url = f"https://dict.youdao.com/dictvoice?audio={word.uk_speech}"
us_url = f"https://dict.youdao.com/dictvoice?audio={word.us_speech}"
# 例如: https://dict.youdao.com/dictvoice?audio=abandon&type=1
```

---

## 七、Word 数据类

### 文件

`src/line_c/domain/word.py`

### 字段

```python
@dataclass
class Word:
    word: str                    # "abandon"
    phonetic: str                # "/ə'bændən/"
    us_phonetic: str = ""        # 美音音标
    uk_phonetic: str = ""        # 英音音标
    us_speech: str = ""          # 有道美音参数
    uk_speech: str = ""          # 有道英音参数
    part_of_speech: str          # "v."
    definition_en: str           # 英文释义
    definition_cn: str           # 中文释义
    examples: List[str]          # 例句列表（旧字段，新数据在 sentences）
    level: str = "cet4"          # cet4 / cet6
    topic_tags: List[str]        # ["daily", "emotion"]
    difficulty: float = 0.5      # 0.0-1.0
    synonyms: List[str]          # 近义词（扁平）
    antonyms: List[str]          # 反义词（扁平）
    grouped_synonyms: List[dict] # 近义词（按词性分组）[{pos, tran, hwds}]
    exam_data: Optional[str]     # 真题 JSON
    sentences: List[dict]        # [{sContent, sCn}] 例句子表
    collocations: List[dict]     # [{pContent, pCn}] 短语子表
```

### 注意

- `examples` 是旧字段（200 词种子数据的遗留），新数据（kajweb/dict）的例句在 `sentences` 里
- `synonyms` 是扁平字符串列表，`grouped_synonyms` 是按词性分组的，数据更丰富
- `sentences` 和 `collocations` 存子表，通过 `_load_sentences()` / `_load_collocations()` 按需加载

---

## 八、VocabularyState — 五阶段状态机

### 文件

`src/line_c/domain/vocabulary_state.py`, `src/line_c/engine/state_machine.py`

### 五阶段

```
UNKNOWN ──→ INTRODUCED ──→ ATTEMPTED ──→ LEARNING ──→ MASTERED
  (未学)      (见过)         (试过)       (复习中)      (已掌握)
```

### 状态转换规则

| 从 | 到 | 触发条件 |
|----|-----|----------|
| UNKNOWN | INTRODUCED | LLM 在对话中用了这个词 |
| UNKNOWN | ATTEMPTED | 用户自己用了这个词（跳级） |
| INTRODUCED | ATTEMPTED | 用户开始主动用这个词 |
| ATTEMPTED | LEARNING | 用户用了 ≥2 次 → 进入 SRS |
| LEARNING | MASTERED | SRS 间隔达到 30 天 |
| ATTEMPTED | INTRODUCED | 回退（用户长时间没用） |
| LEARNING | ATTEMPTED | 回退（复习失败） |

### 用法

```python
from line_c.domain.vocabulary_state import VocabularyState

# 写在 words 表的 state 列中
repo.update_word_state("abandon", VocabularyState.LEARNING)

# 查询某个状态的词
words = repo.get_words_by_state(VocabularyState.LEARNING)
```

---

## 九、SM-2 算法 + SRSScheduler

### 文件

- `src/line_c/engine/sm2_srs.py` — SM-2 纯算法（纯函数）
- `src/line_c/engine/srs_scheduler.py` — 调度器（管理多个词的复习计划）

### SM-2 算法

```python
from line_c.engine.sm2_srs import sm2_calculate

result = sm2_calculate(
    quality=4,          # 回忆质量 0-5（5=脱口而出）
    repetition=2,       # 连续正确次数
    interval=6.0,       # 上次间隔（天）
    ef=2.5,             # 难度因子
)
# → SM2Result(interval_days=15.0, repetition=3, ef=2.46)
```

### 典型间隔序列（quality=5 时）

```
第1次成功 → 1天后
第2次成功 → 6天后
第3次成功 → 15天后
第4次成功 → 38天后
第5次成功 → 97天后
```

### SRSScheduler 用法

```python
from line_c.engine.srs_scheduler import SRSScheduler

scheduler = SRSScheduler()

# 安排复习（ConversationManager 自动调用）
scheduler.schedule("abandon", quality=4)

# 查询今天要复习的词
due_words = scheduler.upcoming_reviews(limit=20)
# → [("abandon", datetime), ...]

# 获取某个词的调度信息
info = scheduler.get("abandon")
# → {"interval": 1.0, "repetition": 1, "ef": 2.5, ...}
```

### 注意事项

- 调度信息存内存（字典），**不持久化**。重启后清空
- 如需持久化，只需把字典序列化到 SQLite，`schedule()` 接口不变

---

## 十、main.py — 组装入口

### 启动方式

```bash
PYTHONPATH=src python src/main.py               # MockLLM + MockTTS
PYTHONPATH=src python src/main.py --llm cloud   # CloudLLM + MockTTS
```

### 组装顺序

```python
# 1. 数据库
repo = VocabularyRepository(DATABASE_PATH)

# 2. LLM（一行切换）
llm = MockLLM()              # 开发
# llm = CloudLLM(api_url=..., api_key=...)  # 联网

# 3. TTS（一行切换）
tts = MockTTS(verbose=True)  # 开发
# tts = PiperTTS(api_url="http://localhost:5002")  # 真机

# 4. 对话管理器（传入上面三个）
manager = ConversationManager(llm=llm, repository=repo, tts=tts)

# 5. 启动会话
manager.start_session(topic="daily life")

# 6. Qt 界面
app = QApplication(sys.argv)
window = MainWindow(manager)
window.show()
app.exec_()
```

### 所有可替换点

| 组件 | 切换位置 | 需要改的文件 |
|------|----------|-------------|
| LLM 后端 | `main.py` 第 70 行 | 只改 `main.py` |
| TTS 后端 | `main.py` 第 73 行 | 只改 `main.py` |
| 数据库路径 | `config.py` | 只改 `config.py` |
| Prompt 模板 | `prompt_builder.py` | `SYSTEM_PROMPT_TEMPLATE` 字符串 |
| 角色设定 | `PromptBuilder()` 参数 | `main.py` 或 `config.py` |

---

## 十一、数据流向速查

```
数据从哪里来
─────────────
kajweb/dict JSONL
  → import_kajweb_dict.py
    → SQLite (data/db/language_learner.db)
      → VocabularyRepository.add_word()
        → Word 对象
          → words 表 + word_sentences 子表 + word_collocations 子表

数据怎么被用
─────────────
用户输入 "I like hiking"
  → ConversationManager._scan_message()
    → VocabularyRepository._batch_lookup()  ← 从 SQLite 查
      → 发现 "hiking" 在词库中
        → update_word_state() → 写入新状态
        → emit word_event()   → UI 更新词汇面板

LLM 回复 "Hiking builds endurance"
  → ConversationManager._scan_message()
    → 发现 "endurance" 在词库中 → INTRODUCED
  → BaseTTS.speak("Hiking builds endurance")
    → 输出语音

学习进度
────────
  _evaluate_progress()（每 5 轮）
    → 找出"见了 N 轮还没用过"的词 → 标记薄弱
    → emit word_event(word, "weak", ...) → UI 标红
```
