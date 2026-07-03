# PROJECT BRIEF: 端侧AI语言学习机 (Edge-AI Language Learner)

> 嵌入式竞赛参赛作品 | 版本 v1.0 归档中 | 2026年6月

---

## 一、我们要做什么

做一台**端侧AI掌上语言学习机**——像 Rabbit R1 那样捧在手里，用语音聊天的方式学英语单词。

**和市面单词机的区别：** 传统单词机是“看单词→选释义”的卡片背诵模式。我们做的是“聊天中自然习得”——AI 朋友在对话中悄悄把生词教给你，像 VocaAI 一样，但**所有 AI 推理都在本地跑，数据不出设备**。

---

## 二、硬件平台

| 项目 | 规格 |
|------|------|
| 主控板 | 飞凌 ELF2 学习板 (瑞芯微 RK3588) |
| CPU | 4×A76 @2.4GHz + 4×A55 @1.8GHz, 8nm |
| NPU | 6 TOPS (INT8), 3个NPU核心 |
| RAM | 8GB LPDDR4 |
| 存储 | 32GB eMMC + M.2 NVMe 插槽 |
| 屏幕 | 飞凌官方 7寸 MIPI DSI (1024×600), 无触摸 |
| 音频 | 板载 Codec 芯片, 板载麦克风, 3.5mm 耳机孔, Speaker 接口 |
| 无线 | M.2 E-Key (需自配 WiFi/BT 模块, 如 AX200) |
| GPIO | 40Pin (树莓派兼容) + 20Pin |
| 供电 | DC 12V (原型机) |
| 系统 | Linux 5.10 + Ubuntu 22.04 (ELF2-Desktop), Qt 5.15 预装 |

---

## 三、技术架构

### 3.1 数据流

```text
[板载麦克风]
    ↓
Silero-VAD
    ↓
SenseVoiceSmall-RKNN2
    ↓
Qwen2.5-1.5B-Instruct
    ↓
Paroli / Piper-RKNN
    ↓
[耳机/喇叭输出]
```

### 3.2 技术栈一览

| 组件 | 选型 |
|------|------|
| VAD | Silero-VAD |
| ASR | SenseVoiceSmall-RKNN2 |
| LLM | Qwen2.5-1.5B-Instruct (w8a8) |
| TTS | Paroli / Piper-RKNN |
| UI | Qt 5.15 |
| 存储 | SQLite |

---

## 四、Line C 当前状态

### v1.0 学习底座（已完成，已提交）

- 词汇库构建（CET-4/CET-6，SQLite）
- LLM 提示词原型（中文焦点词 + 回抛 + 强化）
- 五阶段状态机 + SM-2 间隔复习
- Qt 横屏三栏对话界面
- 中文焦点词驱动
- 学习事件 / 掌握度评分 / 目标词追踪 / 纠错反馈
- CloudLLM 结构化评估

### v2.0 VocaLand 升级（已完成，待提交）

- 用户系统（多角色、英语水平、兴趣标签）
- QStackedWidget 四页面导航（首页 → 话题 → 聊天 → 复习）
- 话题生成器（LLM + fallback + 安全过滤）
- 墨墨式闪卡复习页（SM-2 自评）
- 聊天取词弹窗（QLabel 手动定位单词）
- 自适应 Prompt（5 档英语水平）

### 当前边界

- ChatPage 直接调 LLM，未经过 ConversationManager 学习管线
- 音标未在取词弹窗和复习卡中展示
- RSS 新闻源已建但未接入
- 学习报告 UI 还没单独做
- 触屏未在真机验证

### 当前验收状态

- **168 个单元测试全部通过**
- 当前项目主状态记录在 `DEVELOPMENT_LOG.md`
- v2 实施细节记录在 `IMPLEMENTATION_LOG.md`

---

## 五、团队分工

```text
Line A: 硬件与系统平台
Line B: AI 模型部署管线
Line C: 应用层与交互逻辑
```

### Line C 负责范围

- 词汇库
- Prompt 工程
- 词汇状态机
- 学习评分
- Qt 界面
- SQLite 学习记录
- 目标词追踪
- CloudLLM 评估接口

---

## 六、归档后建议的查看顺序

1. `DEVELOPMENT_LOG.md` — 当前主状态
2. `plans/active/vocaai-linec-upgrade/plan.md` — 归档计划摘要
3. `plans/active/vocaai-linec-upgrade/tasks.md` — 归档任务摘要
4. 源码与测试
