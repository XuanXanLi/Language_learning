# PROJECT BRIEF: 端侧AI语言学习机 (Edge-AI Language Learner)

> 嵌入式竞赛参赛作品 | 版本 v1.0 | 2026年5月 | 开发周期 4周 | 团队 3人

---

## 一、我们要做什么

做一台**端侧AI掌上语言学习机**——像 Rabbit R1 那样捧在手里，用语音聊天的方式学英语单词。

**和市面单词机的区别：** 传统单词机是"看单词→选释义"的卡片背诵模式。我们做的是"聊天中自然习得"——AI 朋友在对话中悄悄把生词教给你，像 VocaAI 一样，但**所有 AI 推理都在本地跑，数据不出设备**。

---

## 二、硬件平台

| 项目 | 规格 |
|------|------|
| 主控板 | **飞凌 ELF2 学习板** (瑞芯微 RK3588) |
| CPU | 4×A76 @2.4GHz + 4×A55 @1.8GHz, 8nm |
| NPU | **6 TOPS (INT8)**, 3个NPU核心, 支持INT4/INT8/FP16 |
| RAM | **8GB LPDDR4** |
| 存储 | 32GB eMMC + M.2 NVMe 插槽 |
| 屏幕 | 飞凌官方 7寸 MIPI DSI (1024×600), 无触摸 |
| 音频 | 板载 Codec 芯片, 板载麦克风, 3.5mm 耳机孔, Speaker 接口 |
| 无线 | M.2 E-Key (需自配 WiFi/BT 模块, 如 AX200) |
| GPIO | 40Pin (树莓派兼容) + 20Pin |
| 供电 | DC 12V (原型机) |
| 系统 | Linux 5.10 + Ubuntu 22.04 (ELF2-Desktop), Qt 5.15 预装 |

**硬件确认清单：**
- [ ] 开发板到手 (已确认)
- [ ] 7寸 MIPI 屏
- [ ] WiFi/BT 模块 (M.2 E-Key)
- [ ] 按键 (3-5个, 接 GPIO)
- [ ] 小喇叭 (接板载 Speaker 接口)
- [ ] 3D 打印外壳

---

## 三、技术架构

### 3.1 数据流

```
[板载麦克风]
    ↓
Silero-VAD          ← 语音活动检测, CPU, <10MB
    ↓
SenseVoiceSmall-RKNN2  ← 语音识别(ASR), NPU核心0, 20x实时, ~1.1GB
    ↓  支持: 中/英/粤/日/韩 + 语种识别 + 情绪检测
    ↓
Qwen2.5-1.5B-Instruct  ← 对话生成(LLM), NPU核心1-2, ~16 tok/s, ~2.5GB
    ↓  w8a8量化, RKLLM推理
    ↓
Paroli / Piper-RKNN    ← 语音合成(TTS), NPU核心0(ASR卸载后), ~200MB
    ↓
[耳机/喇叭输出]
```

### 3.2 技术栈一览

| 组件 | 选型 | 关键指标 |
|------|------|----------|
| VAD | Silero-VAD (sherpa-onnx) | <10MB, CPU |
| ASR | SenseVoiceSmall-RKNN2 | 20x RT, 中英粤日韩, 情绪检测 |
| LLM | Qwen2.5-1.5B-Instruct (w8a8) | ~16 tok/s, ~2.5GB, 双语 |
| TTS | Paroli/Piper RKNN | NPU 4.3x加速, 流式输出 |
| 管线框架 | sherpa-onnx + RKLLM | 统一ASR/VAD/TTS |
| UI | Qt 5.15 (ELF2预装) | 对话气泡 + 状态指示 |
| 存储 | SQLite | 词汇库 + 学习记录 + 偏好 |

### 3.3 8GB 内存预算

```
OS + Qt:              ~1.0 GB
SenseVoice ASR:       ~1.1 GB (用完可卸载)
Qwen2.5-1.5B LLM:     ~2.5 GB (长驻)
Paroli TTS:           ~0.2 GB (ASR卸载后加载)
词汇DB + 应用逻辑:     ~0.3 GB
─────────────────────────────
峰值:                  ~5.1 GB (36% 余量, 安全)
```

---

## 四、AI 模型选型详解

### 4.1 为什么选这些模型

| 组件 | 选定 | 为什么 |
|------|------|--------|
| ASR | **SenseVoiceSmall-RKNN2** | Whisper 官方 RKNN 有 bug (INT8 输出乱码); SenseVoice 社区验证成熟, 20x 实时 |
| LLM | **Qwen2.5-1.5B-Instruct w8a8** | 1.5B 级中英双语最强; 有预转换 .rkllm 可用; 16 tok/s 满足对话延迟 |
| TTS | **Paroli/Piper RKNN** | 唯一验证的 RK3588 NPU TTS; sherpa-onnx 统一框架, 减少集成复杂度 |

### 4.2 LLM 提示词架构 (三层)

借鉴 Duolingo "Video Call with Lily" 的多阶段架构：

**第一层: 系统层 (System Prompt)** — 固定角色设定
```
You are Leo, a patient English tutor and friend.
Learner is at CET-4 level.

RULES:
- Speak naturally, like a friend chatting, NOT like a textbook.
- Target words for today: {target_words}. Weave 1-2 into conversation naturally.
- If the learner code-switches to Chinese, understand and respond in simpler English.
- Gently correct wrong word usage by modeling (don't lecture).
- Every ~5 exchanges, reuse a previous word.
- Keep responses under 50 words. Be encouraging.
```

**第二层: 会话层 (Session Context)** — 动态注入
- 当前 CET 等级
- 本节目标词汇 (3-5个)
- 用户已知词汇列表
- 历史薄弱词

**第三层: 轮次级 (Turn Guard)** — 每轮后检查
- 目标词是否自然使用?
- 用户是否困惑?
- 是否该复习旧词?

### 4.3 词汇学习引擎

**五阶段状态机:**
```
unknown → introduced → attempted → learning → mastered
 (未学)   (对话中见过)  (用户尝试用)  (SRS排期中)  (已掌握)
```

**SM-2 间隔复习算法:**
```
1小时 → 1天 → 3天 → 7天 → 14天 → 30天
```

**内置词库:**
- CET-4: ~4500 词
- CET-6: ~6000 词 (含 CET-4)
- 每词含: 拼写、音标、释义、例句、难度等级、话题标签

---

## 五、团队分工 (3人 × 3线并行)

```
Line A: 硬件与系统平台 (Person A — 也是集成者)
  ├── ELF2 环境搭建 (NPU驱动、音频驱动、交叉编译链)
  ├── 外设调试 (MIPI屏、麦克风、喇叭、按键GPIO)
  ├── 3D 外壳设计与打印
  ├── 系统镜像制作/烧写
  └── [集成] Week 3起串联 Line B + C, 端到端测试

Line B: AI模型部署管线 (Person B)
  ├── sherpa-onnx 编译 + SenseVoiceSmall-RKNN2 部署
  ├── RKLLM 环境搭建 + Qwen2.5-1.5B 转换/加载
  ├── Paroli/Piper TTS + RKNN 部署
  ├── 管线串联 (VAD→ASR→LLM→TTS)
  └── 性能优化 (内存管理、模型按需加载/卸载)

Line C: 应用层与交互逻辑 (Person C)
  ├── 词汇库构建 (CET-4/6词表 + 分级)
  ├── LLM 提示词工程 (角色设定 + 词汇注入 + 轮次管理)
  ├── 词汇状态机 + SRS 引擎
  ├── Qt 对话界面
  └── SQLite 学习记录存储
```

**并行策略:**
- Line B 和 Line C **完全可并行** — C 用 mock LLM 先做逻辑, B 专注在真实硬件上跑通模型
- Person A Week 1-2 专注硬件打底, Week 3-4 转向集成联调

---

## 六、四周时间线

### Week 1 (启动)

| Line | 任务 |
|------|------|
| A | 烧写 Ubuntu 镜像 → 验证 NPU 驱动版本 → 音频外设验证 (arecord/aplay) → MIPI 屏幕点亮测试 |
| B | 研究 rkllama 项目代码结构 → 编译 sherpa-onnx (开启 RKNN) → 跑通 SenseVoiceSmall demo |
| C | 整理 CET-4/CET-6 词表 (JSON) → SQLite Schema 设计 → PC 上原型测试 LLM 三层提示词架构 |

### Week 2 (核心开发)

| Line | 任务 |
|------|------|
| A | 按键 GPIO 焊接与驱动 → 3D 外壳 Fusion 360 初版建模 → 验证 WiFi/BT 模块 |
| B | RKLLM Runtime 环境搭建 → 加载 Qwen2.5-1.5B 并验证 → Paroli TTS 部署与测试 |
| C | 词汇状态机实现 (五阶段模型) → SM-2 SRS 引擎编码 → 对话管理逻辑框架 |

### Week 3 (集成)

| Line | 任务 |
|------|------|
| A | 3D 外壳打印与装配 → 开始集成 Line B + Line C → 管线初步联调 |
| B | ASR→LLM→TTS 管线串联 → 端到端延迟测试与优化 → 模型按需加载/卸载机制 |
| C | Qt 对话界面开发 → 对话气泡 UI + 状态指示 → 词汇学习摘要面板 |

### Week 4 (收尾)

| Line | 任务 |
|------|------|
| A | 端到端集成联调 → 8项验收测试 → 准备演示场景 → 制作烧写镜像 |
| B | 管线性能优化 → Bug 修复 → 异常恢复机制 |
| C | 提示词最终调优 → 演示场景对话设计 → 整体测试与 Bug 修复 |

---

## 七、验收标准

1. **语音对话闭环:** 对着麦克风说中英混合语句 → 2秒内得到英语语音回复
2. **词汇自然插入:** 连续对话 5 轮后, 目标词汇至少被 LLM 自然使用 1 次
3. **离线运行:** 拔掉网线, 完整对话功能正常工作
4. **词汇追踪:** 对话结束后, 新学词汇正确出现在学习记录中, 状态准确更新
5. **全 NPU 加速:** ASR/LLM/TTS 三个模型均运行在 NPU 上 (验证: `cat /sys/kernel/debug/rknpu/load`)
6. **稳定运行:** 连续对话 30 分钟无 OOM、无 NPU 挂死、无音频卡顿
7. **外壳完整:** ELF2 + 屏幕 + 按键装配在 3D 打印外壳中, 外观整洁
8. **个性化记忆:** 重启后, 历史学习词汇记录和用户偏好完整保留

---

## 八、关键参考资料

### 完整管线
- [rkllama](https://github.com/NotPunchnox/rkllama) — 完整 VAD→ASR→LLM→TTS 管线, OpenAI 兼容 API, **最直接的参考实现**
- [paroli-on-orangepi](https://github.com/thanhtantran/paroli-on-orangepi) — Piper TTS + RK3588 NPU 加速
- [useful-transformers (RK3588 fork)](https://github.com/kidVTP/useful-transformers_npu-rk3588) — Whisper on RK3588 NPU

### ASR
- [SenseVoiceSmall-RKNN2](https://huggingface.co/ThomasTheMaker/SenseVoiceSmall-RKNN2) — 预转换 RKNN 模型
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) — 统一 ASR/VAD/TTS 框架, 有 RKNN 后端

### LLM
- [RKLLM 官方](https://github.com/airockchip/rknn-llm) — Rockchip LLM 部署工具链 v1.2.3
- [jamescallander on HuggingFace](https://huggingface.co/jamescallander) — 大量预转换 .rkllm 模型

### TTS
- [paroli-daemon](https://github.com/AmrMantawi/paroli-daemon) — Piper TTS 流式服务器 + RKNN

### 词汇学习
- [DIY-MKG](https://github.com/kenantang/DIY-MKG) — LLM 驱动的个性化词汇知识图谱, MIT 开源

### 硬件设计
- [Retro Lite CM5](https://github.com/StonedEdge/Retro-Lite-CM5) — RK3588S 掌机, 开源 3D CAD
- [The Xela](https://bitbuilt.net/forums/threads/2024-contest-entry-the-xela-an-rk3588s-powered-handheld.6430/) — Orange Pi 5 掌机, 7寸屏, 3D 打印

---

## 九、风险与应对

| 风险 | 影响 | 概率 | 应对 |
|------|------|------|------|
| NPU 驱动版本过低 (<v0.9.8) | RKLLM 无法运行 | 中 | Week 1 首日检查; 从 Rockchip SDK 升级 |
| Qwen2.5-1.5B 无预转换模型 | 需自行转换 | 低 | jamescallander HF 仓库已有; 备选 x86 Linux PC 转换 |
| 端到端延迟 >3s | 对话体验差 | 中 | 流式 TTS; 缩短 LLM 输出; 优化加载策略 |
| 8GB 内存峰值超标 | OOM 进程被杀 | 低 | 按需加载/卸载; INT4 量化降至 ~1.5GB |
| WiFi 模块不可用 | 无法联网测试 | 中 | Week 1 验证; 离线对话是 MVP 核心, 联网可后续 |

---

## 十、当前任务状态

### Line C 完成 (PC端开发)

- [x] **C1: 词汇库构建** — 200词 CET-4 种子数据 (JSON + SQLite), 含音标/释义/例句/话题标签
- [x] **C2: LLM 提示词原型** — 三层提示词架构 (系统层/会话层/轮次级), PromptBuilder + ConversationManager
- [x] **C3: 词汇状态机 + SRS 引擎** — 五阶段状态机 (unknown→introduced→attempted→learning→mastered), SM-2 间隔复习
- [x] **C4: Qt 对话界面** — 聊天气泡 + 状态指示器 + 词汇摘要面板, 500×700 PC开发版窗口
- [x] **测试覆盖** — 83 个单元测试全部通过 (vocabulary_repository, state_machine, sm2_srs, srs_scheduler, prompt_builder, conversation_manager)

### Line A (硬件与系统平台)

- [ ] **A1: ELF2 环境搭建** — 烧写官方 Ubuntu 镜像, 确认 NPU 驱动版本, 安装基础工具链
- [ ] **A2: 音频外设验证** — arecord/aplay 测试板载麦克风和耳机输出
- [ ] **A3: MIPI 屏点亮** — 连接 7寸屏, 测试 Qt demo
- [ ] **A4: 按键 GPIO 接入** — 焊接与驱动
- [ ] **A5: 3D 外壳设计** — Fusion 360 建模 + 打印
- [ ] **A6: 系统镜像制作**

### Line B (AI模型部署管线)

- [ ] **B1: 研究 rkllama 完整管线** — Clone 并分析代码结构
- [ ] **B2: sherpa-onnx 编译** — 开启 RKNN 支持, 运行 SenseVoiceSmall demo
- [ ] **B3: RKLLM 环境搭建** — 编译 Runtime, 加载 Qwen2.5-1.5B
- [ ] **B4: 管线串联** — VAD→ASR→LLM→TTS
- [ ] **B5: 性能优化** — 目标 <3s 端到端延迟

### 后续集成

- [ ] **INT1: 端到端集成** — Line B + Line C 在 ELF2 上联调
- [ ] **INT2: 验收测试** — 8项验收标准

---

## 附录: 给每个 Claude Code 用户的使用指南

把本文件放到你的项目根目录，Claude Code 启动时会自动读取。

**建议的首次对话指令:**
```
/init
```
让 Claude 分析项目结构后补充 CLAUDE.md。

**针对不同角色的启动提示:**

*Line A (硬件/系统):*
> 我负责 ELF2 硬件和系统集成。请帮我[具体任务]。这是嵌赛项目, 1个月交付, ELF2 是飞凌 RK3588 学习板。

*Line B (AI模型):*
> 我负责在 RK3588 上部署 ASR/LLM/TTS 模型管线。请帮我[具体任务]。当前方案: SenseVoiceSmall-RKNN2 + Qwen2.5-1.5B(RKLLM) + Paroli/Piper-RKNN。

*Line C (应用层):*
> 我负责语言学习应用逻辑和 Qt 界面。请帮我[具体任务]。核心功能: 对话中学词汇, 五阶段词汇状态机, SM-2 间隔复习。
