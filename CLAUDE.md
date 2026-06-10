# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

端侧AI语言学习机 (Edge-AI Language Learner) — 嵌入式竞赛作品。
一台基于飞凌ELF2 (RK3588) 的掌上设备，通过语音对话聊天的方式帮助用户学习英语单词。
所有AI推理 (ASR + LLM + TTS) 完全在端侧运行。

**完整项目文档见 [PROJECT_BRIEF.md](./PROJECT_BRIEF.md)** — 包含硬件规格、技术架构、模型选型、团队分工、时间线和任务状态。

**详细技术规格见 [plans/active/language-learner-edge-ai/plan.md](./plans/active/language-learner-edge-ai/plan.md)**

## Key Constraints

- 主控: 飞凌ELF2 (RK3588, 8GB LPDDR4) — 不可更换
- NPU: 6 TOPS INT8, 3 cores
- OS: Linux 5.10 + Ubuntu 22.04 (ELF2-Desktop)
- UI: Qt 5.15 (预装)
- 开发周期: 4周, 团队3人

## Build, Test, and Development Commands

```bash
# 激活虚拟环境（每次新终端都要做）
source venv/bin/activate

# 生成种子词汇 JSON
python scripts/generate_seed_data.py

# 导入 JSON 到 SQLite
python scripts/import_vocabulary.py

# 运行所有测试
PYTHONPATH=src pytest tests/ -v

# 运行单个测试文件
PYTHONPATH=src pytest tests/test_vocabulary_repository.py -v

# 运行引擎演示（看每个模块在干什么）
PYTHONPATH=src python scripts/demo_engine.py

# 启动应用（MockLLM，无需联网）
PYTHONPATH=src python src/main.py

# 启动应用（云端 API，先设置密钥）
export CLOUD_API_KEY=sk-your-key-here
PYTHONPATH=src python src/main.py --llm cloud
```

## Git 工作流与代码管理

远程仓库：https://github.com/XuanXanLi/Language_learning.git

### 日常提交流程

改完代码后：
```bash
git add -A
git commit -m "简短描述做了什么改动"
git push
```

### 分支策略

- `main` 分支 = 稳定版本，只有确认没问题才推
- 开发新功能前先开分支，避免弄坏 main：

```bash
# 开新分支做实验
git checkout -b feature/功能名

# 改代码... 测试...

# 搞砸了？回到 main 的干净状态
git checkout main

# 满意了？合入 main
git checkout main
git merge feature/功能名
git push
```

### 代码回流

任何时候想回到初始版本：
```bash
git checkout main        # 回到主分支，一切恢复原样
```

当用户说"更新代码""提交代码""推代码""push"时，执行日常提交流程。
当用户说"开分支""做新功能"时，先开分支再改代码。
修改代码前（开分支后），必须遵守规则 5 征得用户同意。

## 用户角色与教学要求

当前用户是 **Line C 负责人**，同时是 **Linux 开发新手**。

### 教学规则（必须遵守）

1. **每个专业术语首次出现时必须解释**：用大白话说明它是什么、干什么用的。不能假设用户已经知道。
2. **每个技术决策必须解释为什么**：不只是说"用A不用B"，要解释A和B的区别以及选择A的理由。
3. **每个命令/工具必须解释**：比如 `pip install` 是什么、`python3 -m venv` 在做什么。
4. **不跳过任何"基础"概念**：没有概念太基础而不值得解释。用户在学习阶段。
5. **修改代码前必须征得用户明确同意（最高优先级）**：
   
   在发起任何修改代码的操作（Write、Edit）之前，必须先用中文向用户说明：
   - **要改什么**：具体哪个文件，改什么内容
   - **为什么这样改**：问题的根因是什么
   - **预期效果**：改完之后会怎么样
   
   然后**等待用户明确同意**（说"可以""同意""开始"等）后才能执行。不能说"我来修一下"就直接动手。
   
   对于只读操作（Read、Bash 查看/运行测试、grep 搜索等），不需要等同意，但也要先说明在做什么。
   哪怕只是一个简单的 `ls` 或 `mkdir`，也要先说一句。

### 术语解释风格示例

- "mock" → "模拟/替身 —— 一个假装是真实模块的假对象。比如真实LLM需要NPU加速，但我们用mock LLM返回固定回复，这样在PC上就能先跑通逻辑，不用等硬件就绪。就像演员排练时用替身走位一样。"
- "SQLite" → "一种轻量级数据库，把所有数据存到单个文件里，不需要单独安装数据库服务。手机App和嵌入式设备最爱用它。"

### 当前角色

- 负责 **Line C：应用层与交互逻辑**
- 在本地 Linux PC 上开发，完成后移植到 ELF2 开发板
- 开发顺序：C1（词汇库）→ C2（提示词原型）→ C3（状态机+SRS）→ C5（Qt界面）

## 归档规则

当用户说以下任意关键词时，触发归档流程：
- "归档"
- "存档"
- "archive"
- "差不多可以归档了"
- "整理一下"

**归档流程（必须执行）：**
1. 检查 `DEVELOPMENT_LOG.md`，确保当前阶段的关键决策已记录
2. 更新 `DEVELOPMENT_LOG.md`，补充本阶段新产生的决策和原因
3. 更新 `PROJECT_BRIEF.md` 中"当前任务状态"一节
4. 检查是否有未提交的代码变更，列出待提交清单
5. 输出一份归档摘要（100 字以内），包含：本阶段做了什么、关键决策、当前状态、下一步
6. **不删除任何代码或文件**——归档只是记录，不是清理

用户说"归档"时，不要等待确认，直接执行上述 6 步。
