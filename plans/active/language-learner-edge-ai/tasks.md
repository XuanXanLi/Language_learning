# Tasks: 端侧AI语言学习机

## Now

- [ ] **LC-ISSUE-1: AI 回复词汇追踪范围过大** — 当前 `_scan_llm_response` 扫描 AI 回复中的所有 CET 词汇。正确逻辑：只追踪 AI 翻译中文词时产出的英文词（即"AI 复述用户中文意思"那段里的词），不应追踪后续普通对话里的 CET 词。
- [ ] **LC-ISSUE-2: 同一词双重状态** — 一个词同时出现在"目标词"和"你用过"中（AI 引入→target 事件，用户后续使用→used 事件，面板没有去重合并）。正确逻辑：一个词面板上只显示一个标签，默认显示最高阶段的状态（学习中 > 你用过 > 目标词）。
- [ ] **A1: ELF2环境搭建** — 烧写官方Ubuntu镜像，确认NPU驱动版本，安装基础工具链 (gcc, cmake, python3, git)。验证 `cat /sys/kernel/debug/rknpu/version` 返回的NPU驱动版本。
- [ ] **B1: 研究rkllama完整管线** — Clone并尝试编译rkllama项目，分析其代码结构（VAD→ASR→LLM→TTS如何串联），输出一份管线数据流分析文档。

## Next

- [ ] A2: 音频外设验证 — 用arecord/aplay测试板载麦克风和耳机输出，确认Codec驱动正常
- [ ] A3: MIPI屏点亮 — 连接官方7寸屏，确认显示正常，测试Qt demo
- [ ] B2: sherpa-onnx编译 — 在ELF2上编译sherpa-onnx（开启RKNN支持），运行SenseVoiceSmall demo
- [ ] B3: RKLLM环境搭建 — 编译/安装RKLLM Runtime，加载测试模型，跑通demo
## Later

- [ ] A4: 按键GPIO接入 — 设计按键布局(3-5键)，焊接按键，编写GPIO驱动
- [ ] A5: 3D外壳设计 — Fusion 360建模，参考Retro Lite CM5/The Xela，适配ELF2板型
- [ ] A6: 系统镜像制作 — 将所有组件打包为可烧写的镜像
- [ ] B4: 管线串联 — VAD→ASR→数据格式转换→LLM→数据格式转换→TTS，跑通端到端
- [ ] B5: 性能优化 — 模型按需加载/卸载，内存管理，目标端到端<3s
- [ ] INT1: 端到端集成 — Line A+B+C串联，完整对话闭环测试
- [ ] INT2: 验收测试 — 按plan.md的8条Acceptance Checks逐条验证

## Blocked

_无阻塞项_

## Done

- [x] 项目规划与调研 — 技术选型、硬件确认、内存预算分析、参考项目调研 (2026-05-14)
- [x] 文档输出 — plan.md, context.md, tasks.md, PRD_端侧AI语言学习机.docx, PROJECT_BRIEF.md (2026-05-14)
- [x] C1-C5: Line C 全部完成 + Phase 5 调优验证 (2026-05-22)
  - 架构: VocaAI 风格，对话驱动，无预设目标词，全量扫描 CET 词汇
  - 83 项测试全通过
  - DeepSeek API 集成，真实 AI 对话可用
  - 修复: 对话历史顺序 Bug（用户消息在 LLM 调用后才加入）
