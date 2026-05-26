# Plan: 端侧AI语言学习机 (Edge-AI Language Learner)

## Problem

市面上的单词学习机都是"单词卡背诵"模式——看单词选释义、拼写测试。没有人真正把**对话中自然习得词汇**这件事做成端侧设备。VocaAI 证明了"聊天中学单词"的产品逻辑可行，但它跑在云端，有延迟、有隐私顾虑、需要订阅付费。

我们要做的是：**一台能捧在手里的端侧AI对话伙伴，在日常聊天中帮你学会英语单词。** 所有AI推理在本地完成，数据不出设备，零延迟，零月费。

## Goals

1. **语音对话学英语**：用户用中英混合语音输入，设备用英语语音回复，在聊天的过程中自然引入目标词汇
2. **全端侧AI**：ASR + LLM + TTS 全部跑在ELF2开发板（RK3588）上，不依赖云端
3. **词汇分级体系**：内置CET-4/CET-6等词汇库，对话场景按等级渐进，系统追踪每个词汇的学习状态
4. **个性化记忆**：记住用户哪些词总是用错、发音哪里有问题、偏好什么话题
5. **极简掌机形态**：类似Rabbit R1的外观，少量按键，使用官方7寸MIPI屏，3D打印外壳
6. **音色克隆预留**：第一版使用固定声线，但架构预留音色克隆的接入点

## Anti-Goals (第一版不做)

- **不做触屏交互**：第一版纯语音+少量按键，简洁优先
- **不做音色克隆**：预留接口但不实现，避免分散精力
- **不做后端App**：学习进度存在本地SQLite，App后续升级再加
- **不做多语言**：先只做英语学习，德语/粤语等架构支持但第一版不开启
- **不做实时新闻搜索**：联网搜索对话内容为可选增强，MVP先走离线对话
- **不做麦克风阵列/远场降噪**：近场单麦即可
- **不做电池供电**：第一版DC 12V供电，原型机不需要移动性

## Constraints

| 约束 | 详情 |
|------|------|
| 主控板 | 飞凌ELF2 (RK3588, 8GB LPDDR4) — 不可更换 |
| NPU算力 | 6 TOPS INT8，3个NPU核心 |
| 内存预算 | 8GB总计，OS约1GB，AI管线峰值约5GB |
| 屏幕 | 飞凌官方7寸MIPI DSI屏 (1024×600) |
| 音频输入 | 板载Codec + 板载麦克风 |
| 音频输出 | 3.5mm耳机孔/板载Speaker接口 |
| 操作系统 | Linux 5.10 + Ubuntu 22.04 (ELF2-Desktop) |
| 开发周期 | **1个月（嵌赛作品）** |
| 团队 | **3人**，有单片机基础，嵌入式Linux边做边学 |
| 外壳 | 3D打印，参考Retro Lite CM5/Xela的掌机设计 |

## Research Notes

### 参考资料项目

**全管线参考（最接近我们目标的）：**
- **rkllama** (`NotPunchnox/rkllama`): Ollama替代品，跑在RK3588上。完整管线 VAD→Whisper(RKNN)→LLM(RKLLM)→Piper TTS，OpenAI兼容API。最直接的参考实现。
- **tkvoice** (UBTECH/优必选): ROS2节点化设计 ASR→LLM→TTS，模块化值得学习，但需要多板。
- **"rk3588离线语音交互"** (proginn.com): sherpa-onnx + RKLLM + YOLOv8，单板全离线方案。

**ASR 参考：**
- **SenseVoiceSmall-RKNN2** (`ThomasTheMaker/SenseVoiceSmall-RKNN2` on HuggingFace): 20x实时，支持中英粤日韩，情绪检测。强烈推荐。
- **Zipformer双语** (sherpa-onnx): WER最低(10.93%)，121MB模型，流式识别。

**TTS 参考：**
- **paroli-daemon** (`AmrMantawi/paroli-daemon`): Piper + RKNN NPU加速，4.3x CPU，流式输出，HTTP/WebSocket服务。
- **paroli-on-orangepi** (`thanhtantran/paroli-on-orangepi`): 同上，专门针对RK3588/3566。

**LLM 参考：**
- **RKLLM官方** (`airockchip/rknn-llm`): v1.2.3，支持Qwen2.5全系列。Qwen2.5-1.5B w8a8 ≈ 16 tok/s, 2.5GB。
- **预转换模型** (`jamescallander` on HuggingFace): 大量.rkllm可直接用，免去转换步骤。
- **DIY-MKG** (`kenantang/DIY-MKG`): LLM驱动的个性化词汇知识图谱构建，MIT开源。

**硬件/外壳参考：**
- **Retro Lite CM5** (`StonedEdge/Retro-Lite-CM5`): RK3588S掌机，3D打印外壳，5.5寸屏，完整开源CAD。
- **The Xela** (`bitbuilt.net`): Orange Pi 5(RK3588S)掌机，7寸屏，3D打印外壳，GBA横版形态。
- **AI Bunny** (UNIHIKER K10): Rabbit R1风格AI伴侣，4块3D打印外壳，结构简单。

### 关键技术决策来源

| 决策 | 依据 |
|------|------|
| ASR选SenseVoice而非Whisper | Whisper RKNN INT8量化有bug(官方Issue #314)，输出乱码；SenseVoice已验证20x实时 |
| LLM选Qwen2.5-1.5B | 双语能力在1.5B级最强；有预转换.rkllm可用；16 tok/s满足对话延迟；2.5GB适配8GB预算 |
| TTS选Piper via Paroli | 唯一验证过的RK3588 NPU加速TTS(4.3x)；sherpa-onnx统一框架降低集成复杂度 |
| 管线框架选sherpa-onnx | 同时支持ASR+VAD+TTS，有RKNN后端，一个框架减少依赖 |
| 架构设计参考Duolingo模式 | 多阶段提示词架构(准备→对话→评估)比单一大提示词更稳定，避免LLM角色漂移 |

### 内存预算验证

```
OS + Qt:              ~1.0 GB
SenseVoice ASR:       ~1.1 GB (NPU core 0, 用后卸载)
Qwen2.5-1.5B LLM:     ~2.5 GB (NPU cores 1-2)
Paroli TTS:           ~0.2 GB (NPU core 0, ASR卸载后加载)
词汇数据库 + 应用:     ~0.3 GB
-------------------------------------------
峰值合计:              ~5.1 GB (8GB预算内, 36%余量)
```

## Chosen Approach

### 技术栈

```
┌─────────────────────────────────────────────────────────┐
│                  ELF2 (RK3588 + 7" MIPI DSI)             │
│                                                         │
│  [板载麦克风] ──→ Silero-VAD ──→ SenseVoiceSmall-RKNN2  │
│                    (sherpa-onnx)   (NPU, 20x RT)         │
│                                         │                │
│                                         ▼                │
│                               Qwen2.5-1.5B-Instruct      │
│                               (RKLLM, NPU, ~16 tok/s)    │
│                               + 词汇状态机 + SRS引擎      │
│                                         │                │
│                                         ▼                │
│                               Paroli/Piper-RKNN          │
│                               (NPU, 4.3x CPU)            │
│                                         │                │
│                                         ▼                │
│                                  [耳机/喇叭输出]          │
│                                                         │
│  UI: Qt 5.15 (官方预装) — 简洁对话界面                    │
│  存储: SQLite (词汇库 + 学习记录 + 用户偏好)              │
│  通信: 管线内用Unix Socket/ZMQ，对外预留HTTP API          │
└─────────────────────────────────────────────────────────┘
```

### LLM 提示词策略 (借鉴Duolingo多阶段架构)

不把所有指令塞进一个提示词。分三层：

1. **系统层(System Prompt)**：固定角色设定——"你是一个耐心的英语母语朋友/老师，名叫Leo。..."
2. **会话层(Session Context)**：动态注入——当前CET等级、本节目标词汇列表(3-5个)、用户已知词汇、历史薄弱词
3. **轮次级(Turn Guard)**：每轮后检查——是否自然使用了目标词？用户是否表现出困惑？下次轮换是否该复习之前的词？

```python
# 伪代码：系统Prompt结构
SYSTEM_PROMPT = """
You are {persona_name}, a patient English tutor and friend.
Your learner is at {cefr_level} level (approximately {vocab_size} words known).

RULES:
- Speak naturally, like a friend chatting, NOT like a textbook.
- Today's target words: {target_words}. Weave 1-2 of them into the conversation naturally.
- If the learner code-switches to Chinese, understand it and respond in English with simpler phrasing.
- If the learner uses a target word incorrectly, gently correct by modeling the correct usage (don't lecture).
- After every ~5 exchanges, subtly ask a question that reuses a previous word.
- Keep responses under 50 words. Be encouraging.

Learner's weak words (use these more often): {weak_words}
Conversation topic preference: {preferred_topic}
"""
```

### 词汇学习引擎

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 词汇库        │    │ 对话分析器    │    │ SRS调度器     │
│              │    │              │    │              │
│ CET-4: 4500词│───→│ 每轮对话后    │───→│ 间隔重复调度  │
│ CET-6: 6000词│    │ 检查:        │    │              │
│ 自定义词库    │    │ - 目标词出现? │    │ 1h→1d→3d→7d  │
│              │    │ - 用户用了吗? │    │ →14d→30d     │
│              │    │ - 用得对吗?   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                  ┌──────────────┐
                  │ 学习状态DB    │
                  │ (SQLite)     │
                  │              │
                  │ word │ state ││
                  │      │ count ││
                  │      │ last  ││
                  │      │ level ││
                  └──────────────┘
```

词汇状态机：`unknown → introduced(对话中出现过) → attempted(用户尝试用过) → learning(SRS排期中) → mastered(SRS完成)`

### 三条并行工作线

```
Line A: 硬件与系统平台 (Person A — 也是集成者)
  ├── ELF2环境搭建 (NPU驱动、音频驱动、交叉编译链)
  ├── 外设调试 (MIPI屏、麦克风、喇叭、按键GPIO)
  ├── 3D外壳设计与打印
  ├── 系统镜像制作/烧写
  └── [集成] 串联Line B + Line C，端到端测试

Line B: AI模型部署管线 (Person B)
  ├── sherpa-onnx编译 + SenseVoiceSmall-RKNN2部署
  ├── RKLLM环境搭建 + Qwen2.5-1.5B转换/加载
  ├── Paroli/Piper TTS + RKNN部署
  ├── 管线串联 (VAD→ASR→LLM→TTS数据流)
  └── 性能优化 (内存管理、模型按需加载/卸载)

Line C: 应用层与交互逻辑 (Person C)
  ├── 词汇库构建 (CET-4/6词表 + 分级)
  ├── LLM提示词工程 (角色设定 + 词汇注入 + 轮次管理)
  ├── 词汇状态机 + SRS引擎
  ├── Qt对话界面
  └── SQLite学习记录存储
```

**关键并行策略：**
- Line B 和 Line C 可以**完全并行**开发：C用mock LLM(本地文件)先做逻辑，B专注把模型跑通
- Line A 的硬件调试和B的模型部署有少量依赖（驱动→NPU SDK），但Week 1可以并行启动
- Person A 作为集成者，Week 1-2专注于硬件打底，Week 3-4转向集成联调

## Rejected Alternatives

| 方案 | 理由 |
|------|------|
| Whisper tiny/base (RKNN官方) | INT8量化有已知bug输出乱码，社区不推荐 |
| 更大LLM (Phi-3-3.8B / MiniCPM3-4B) | 8GB内存不够同时加载ASR+LLM+TTS；需16GB板 |
| GPT-SoVITS / CosyVoice | 太重(2-4GB)，第一版不需要音色克隆 |
| Android系统 | ELF2官方BSP是Linux+Qt；用Android增加未知风险 |
| PyQt5 / 其他GUI框架 | ELF2预装Qt 5.15，用现成的减少环境问题 |
| 纯CPU推理 (llama.cpp) | NPU加速3-5x，功耗低一半；嵌赛需要突出端侧AI优势 |

## Acceptance Checks

1. **语音对话闭环**：对着板载麦克风说中英混合语句 → 2秒内得到英语语音回复
2. **词汇自然插入**：连续对话5轮后，目标词汇至少被LLM使用1次
3. **离线运行**：拔掉网线，完整对话功能正常工作
4. **词汇追踪**：对话结束后，新学词汇出现在学习记录中，状态正确更新
5. **全NPU加速**：ASR/LLM/TTS三个模型均运行在NPU上（可通过/sys/kernel/debug/rknpu/load验证）
6. **稳定运行**：连续对话30分钟无内存溢出、无NPU挂死
7. **外壳完整**：ELF2+屏幕+按键装配在3D打印外壳中，外观整洁
8. **个性化记忆**：重启后，之前学过的词汇和偏好仍然保留
