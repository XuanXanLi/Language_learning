# Context: 端侧AI语言学习机

## 项目背景

嵌赛作品，1个月交付。3人团队，有单片机基础，嵌入式Linux边做边学。

## 硬件确认

- **主控**: 飞凌ELF2学习板，RK3588，8GB LPDDR4，32GB eMMC
- **屏幕**: 飞凌官方7寸MIPI DSI (1024×600)，无触摸
- **音频**: 板载Codec芯片(NAU88C22YG或同系列)，板载咪头，3.5mm耳机孔，Speaker接口
- **无线**: M.2 E-Key插槽，需自配WiFi/BT模块(如AX200/AX210)
- **按键**: 通过40Pin GPIO接入，具体数量和布局待定
- **外壳**: 3D打印，参考Retro Lite CM5和The Xela的掌机设计
- **供电**: DC 12V（原型机阶段）

## 技术决策 (已锁定)

| 组件 | 选择 | 锁定原因 |
|------|------|----------|
| ASR | SenseVoiceSmall-RKNN2 via sherpa-onnx | 唯一验证的RK3588 NPU多语言ASR，20x实时 |
| LLM | Qwen2.5-1.5B-Instruct w8a8 via RKLLM | 双语最优，16 tok/s，2.5GB，预转换模型可用 |
| TTS | Paroli/Piper RKNN via sherpa-onnx | NPU加速4.3x，流式输出 |
| 管线框架 | sherpa-onnx + RKLLM | 统一ASR/VAD/TTS，减少集成复杂度 |
| UI | Qt 5.15 (ELF2预装) | 零额外依赖，官方BSP内置 |
| 存储 | SQLite | 轻量，本地，无需服务端 |
| 系统 | Ubuntu 22.04 (ELF2-Desktop) | 官方镜像，预装OpenCV/TFLite/PyTorch |

## 关键参考资料

### 最接近的完整项目
- **rkllama** (`github.com/NotPunchnox/rkllama`): 完整VOICE→ASR→LLM→TTS管线 + OpenAI API
- **paroli-on-orangepi** (`github.com/thanhtantran/paroli-on-orangepi`): Piper TTS + RK3588 NPU
- **useful-transformers** (`github.com/moonshine-ai/useful-transformers`): Whisper on RK3588 NPU

### 预转换模型
- SenseVoiceSmall-RKNN2: `huggingface.co/ThomasTheMaker/SenseVoiceSmall-RKNN2`
- Qwen2.5-1.5B预转换: `huggingface.co/jamescallander` (搜索qwen2.5-1.5B)

### 硬件设计参考
- Retro Lite CM5 CAD: `github.com/StonedEdge/Retro-Lite-CM5`
- The Xela worklog: `bitbuilt.net` (search "The Xela RK3588S")

### 学习资源
- RK3588 Zipformer双语部署: CSDN `qq_42910179`
- sherpa-onnx官方文档: `github.com/k2-fsa/sherpa-onnx`
- RKLLM官方: `github.com/airockchip/rknn-llm`

## 词汇库

第一版内置：
- CET-4: ~4500词
- CET-6: ~6000词 (含CET-4)
- 以JSON/SQLite格式存储，每个词包含：拼写、音标、释义、例句、难度等级、话题标签

## 音色克隆预留点

在TTS模块中预留接口：
```python
# 预留：未来替换为MOSS-TTS-Nano
def synthesize_speech(text: str, voice_profile: str = "default") -> bytes:
    if voice_profile == "default":
        return paroli_synthesize(text)
    else:
        # TODO: 接入MOSS-TTS-Nano音色克隆
        raise NotImplementedError("Voice cloning in next release")
```

## 已知风险

1. **NPU驱动版本**: ELF2预装NPU驱动可能是v0.9.5，RKLLM ≥1.2.1需要v0.9.8+。可能需要升级驱动。
2. **Qwen2.5-1.5B RKLLM转换**: 如果没有现成的预转换模型，需要x86 Linux PC做转换（不能用Windows）
3. **音频延迟**: 完整管线 (ASR→LLM→TTS) 端到端延迟目标<3秒，需实测验证
4. **WiFi模块**: 需确认ELF2的M.2 E-Key是否已焊接、驱动是否就绪

## 恢复笔记 (2026-05-14)

上次会话完成:
- 完整技术调研 (ASR/LLM/TTS/NPU工具链/参考项目)
- plan.md 定稿 (三线并行方案确认)
- 输出: PRD_端侧AI语言学习机.docx, PROJECT_BRIEF.md
- CLAUDE.md 更新指向项目文档

下次启动:
- 3人团队各自认领 Line A/B/C
- A 开始 ELF2 环境搭建 (烧写镜像、查NPU驱动版本)
- B 开始研究 rkllama 管线代码结构
- C 开始词汇库构建 + 提示词原型
- 项目根目录有完整文件，Claude Code 会自动读取
