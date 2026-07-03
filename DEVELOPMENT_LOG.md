# 开发日志：Line C / VocaLand v2 归档主文档

> 这是当前项目的**单一主状态文档**：记录已完成内容、当前边界、开发规则和后续方向。其它计划文件只保留简短归档摘要。

---

## 1. 当前项目状态

**Line C 已完成 VocaLand v2 升级（2026-07-01），中文 RSS + 预览弹窗 + 文章正文提取 + 加载动画已完成（2026-07-04）。**

系统现在具备两层架构：

**v1.0 学习底座（保留，继续工作）：**
- 词汇库 + SQLite 持久化
- 五阶段状态机 `UNKNOWN → INTRODUCED → ATTEMPTED → LEARNING → MASTERED`
- SM-2 间隔复习
- 三层 PromptBuilder
- ConversationManager 学习事件链路
- 学习事件 / 掌握度评分 / 学习评估
- 目标词追踪器 `TargetWordTracker`
- CloudLLM 结构化 JSON 评估（失败自动回退规则评估）
- 纠错反馈消息流

**v2.0 VocaLand 升级（新增，已集成）：**
- QStackedWidget 多页面导航框架（首页 → 话题 → 聊天 → 复习）
- 用户系统（多角色、英语水平、兴趣标签）
- 话题生成器（LLM 驱动 + 安全过滤 + fallback）
- 墨墨式闪卡复习页（翻转 + SM-2 自评 + 完成统计）
- 聊天取词弹窗（QLabel + mousePressEvent 手动定位单词）
- 自适应 Prompt（根据角色英语水平调整 persona，5 档）

**v2.1 中文 RSS + 预览弹窗（2026-07-03 新增，2026-07-04 完善）：**
- 中文 RSS 信息源（8 个类别 18 个中文源，替代全部英文源）
- 持久化每日缓存（`data/rss/feed_cache.json`，同一日内不重复抓取）
- AI 内容筛选（Cloud 模式 LLM 五维度审核，Mock 模式规则过滤）
- 话题预览弹窗（AI 中文摘要 + 英语讨论引导问题）
- 中文敏感词过滤（23 个中文关键词）
- **Bug 修复**：卡片点击信号参数覆盖闭包变量（`lambda checked, t=topic`）
- **预览弹窗优化**：摘要 + 讨论引导合并到同一滚动区域，修复内容显示不全
- **文章正文提取**：`article_extractor.py` — 从原文 URL 抓取完整文章内容，LLM 摘要更丰富
- **加载动画**：选角色后显示转圈等待 + 30 秒超时降级，不再立即显示预设话题

当前测试状态：**168 个单元测试全部通过**。

---

## 2. 已完成内容

### v1.0 学习底座（已提交 `8435a41`）

- **C1 词汇库构建**
  - CET-4 / CET-6 词库导入到 SQLite
  - 扩展了例句、短语、音标、难度、状态字段

- **C2 LLM 提示词原型**
  - 中文焦点词优先
  - 最近词汇回抛
  - 薄弱词强化

- **C3 状态机 + SRS**
  - 五阶段学习状态
  - SM-2 间隔复习
  - `SRSScheduler` 继续可用

- **C4 Qt 对话界面**
  - 横屏三栏布局
  - 对话区、角色区、词汇面板

- **C5 中文焦点词驱动**
  - 用户中文词 → AI 翻译 → 英文词追踪

- **学习底座组件**
  - `LearningEventType` / `LearningEvent` / `EvaluationResult`
  - `LearningEvaluator` / `MasteryScorer` / `TargetWordTracker`
  - `word_mastery` 表 / `learning_events` 表
  - `pending_correction` 纠错重试状态
  - CloudLLM 结构化评估支持

### v2.0 VocaLand 升级（待提交）

- **Phase 0: 数据层** — 3 个 domain 数据类 + 3 个 repository + 3 张新 SQLite 表
  - `UserProfile` / `UserRepository` — 多角色管理
  - `ChatSession` / `ChatSessionRepository` — 会话记录
  - `UserVocabulary` / `UserVocabularyRepository` — 用户词汇状态

- **Phase 1: 导航框架 + 四页面**
  - `main_window.py` 重写为 `QStackedWidget` 导航壳
  - `HomePage` — 角色卡片列表 + 创建/编辑/删除弹窗
  - `TopicFeedPage` — 话题卡片 + 自定义输入 + 复习入口
  - `ChatPage` — 两栏布局 + `_TappableBubble` + 生词面板
  - `ReviewPage` — 墨墨式闪卡复习 + SM-2 自评

- **Phase 2: 话题生成**
  - `TopicGenerator` — LLM 驱动 + hardcoded fallback
  - 安全过滤：阻止政治/暴力/成人内容关键词

- **Phase 3: 聊天核心**
  - `_TappableBubble` — QLabel + mousePressEvent 手动定位单词
  - `WordPopup` — 查词弹窗（本地DB → CloudLLM → 兜底）
  - 自适应 Prompt — 根据角色英语水平调整（5 档）
  - 去抖发送

- **Phase 4: 复习系统**
  - `ReviewSessionManager` — SM-2 评分 + 掌握判定 + 抽查
  - 正面/背面翻转 + 三按钮自评 + 完成统计

- **Phase 5: 集成**
  - 迁移脚本 `v2_migration.py`
  - `main.py` 重写为 v2 入口（依赖注入所有 repository 和 engine）
  - `vocabulary_repository.py` 扩展（新增 `get_word_mastery` 等方法）
  - `conversation_manager.py` 增强（集成 evaluator/scorer/tracker）

---

## 3. 当前开发边界

### 已完成，不再优先改

- 核心学习评分底座（v1.0）
- v2 导航框架和四页面
- 用户系统和角色管理
- 话题生成器
- 闪卡复习系统
- 取词弹窗
- CloudLLM 结构化评估
- **中文 RSS 新闻源接入 + 每日缓存**（2026-07-03）
- **话题预览弹窗**（AI 摘要 + 讨论引导）（2026-07-03）
- **文章正文提取 + 预览滚动修复 + 加载动画**（2026-07-04）

### 还需要完善

1. **ConversationManager 迁移到 v2 ChatPage**
   - ChatPage 目前直接调用 LLM，未经过 ConversationManager 的学习事件链路
   - 后续需要把学习评估管线接入聊天页

2. **音标数据补齐**
   - 取词弹窗和复习卡片翻转时，音标未从 DB 获取

3. **学习报告 UI**
   - 会话总结字段已有，但无独立报告页

4. **触屏适配**
   - mousePressEvent 同时响应触屏和鼠标，但未在真机上验证

5. **SRS 持久化**
   - 复习队列目前为会话内逻辑

---

## 4. 开发规则

1. **先读再写** — 改代码前必须先读当前实现和直接调用方
2. **最小改动** — 只改必要部分，不重写已有稳定模块
3. **保留骨架** — 继续沿用 `domain / engine / ui` 分层
4. **学习逻辑优先于 UI** — 先把"学什么、怎么评估、怎么纠错"做对
5. **测试必须跟上** — 每次改动后跑相关测试，最后跑全量测试
6. **CloudLLM 用于验收，不作为唯一依赖** — 规则评估必须能回退
7. **自由聊天不要批量纠错** — 轻纠错策略优先
8. **不破坏现有状态机和 SQLite 数据** — 新功能增量接入
9. **UI 组件选择** — QLabel 显示文本，QTextBrowser 多行只读，禁止 QTextEdit + setFixedSize 组合
10. **布局清理** — `while layout.count(): takeAt(0)` 模式，递归处理嵌套布局

---

## 5. 已确认的技术决策

- **数据库**：SQLite（单文件，嵌入式友好）
- **状态机**：保留五阶段（UNKNOWN → INTRODUCED → ATTEMPTED → LEARNING → MASTERED）
- **复习算法**：SM-2（间隔重复）
- **LLM 接口**：抽象基类 `BaseLLM`
- **云端模型**：CloudLLM / DeepSeek 风格兼容 API
- **UI 框架**：Qt 5.15（ELF2 预装）
- **导航模式**：QStackedWidget 多页面（v2 新增）
- **取词方式**：QLabel + mousePressEvent + QFontMetrics 手动定位（v2 新增，替代 QTextEdit.cursorForPosition）
- **话题生成**：LLM 驱动 + hardcoded fallback + 安全过滤（v2 新增）
- **依赖注入**：main.py 创建所有实例并注入（v2 新增）

---

## 6. 待提交清单

当前工作区有大量未提交变更（v2 升级全部内容）：

**新建文件（约 30 个）：**
- Domain: `chat_session.py`, `learning_event.py`, `user_profile.py`, `user_vocabulary.py`
- Engine: `chat_session_repository.py`, `learning_evaluator.py`, `mastery_scorer.py`, `review_session_manager.py`, `rss_feed_fetcher.py`, `target_word_tracker.py`, `topic_generator.py`, `user_repository.py`, `user_vocabulary_repository.py`
- UI: `pages/` (4 页面 + `__init__`), `widgets/` (word_popup + `__init__`)
- Tests: 9 个新测试文件
- 文档/配置: `IMPLEMENTATION_LOG.md`, `.claude/rules/v2-coding-rules.md`, VocaAI 调研报告
- 脚本: `v2_migration.py`
- 计划: `plans/active/vocaai-linec-upgrade/` (5 个文件)

**修改文件（10 个）：**
- `conversation_manager.py`, `vocabulary_repository.py`, `main_window.py`, `word_summary.py`, `main.py`, `test_conversation_manager.py`, `test_vocabulary_repository.py`
- `config.py`（+RSS 缓存路径）
- `rss_feed_fetcher.py`（中文源 + 每日缓存 + AI 筛选 + 预览）
- `topic_generator.py`（中文关键词 + 预览生成 + 移除翻译）
- `topic_feed_page.py`（卡片点击 → 预览弹窗）
- `DEVELOPMENT_LOG.md`

**新建文件（+4 个）：**
- `rss_cache_manager.py`（持久化每日缓存）
- `ui/widgets/topic_preview.py`（预览弹窗）
- `engine/article_extractor.py`（文章正文提取）

**删除文件（2 个）：**
- `gemini-code-1779790654150.html`, `test_results.txt`

---

## 7. 归档后的维护方式

后续继续开发，优先看这个顺序：

1. `DEVELOPMENT_LOG.md` — 当前主状态（本文件）
2. `IMPLEMENTATION_LOG.md` — v2 实施细节和文件清单
3. `PROJECT_BRIEF.md` — 项目总览和 Line 划分
4. `plans/active/vocaai-linec-upgrade/` — 计划文档
5. 源码和测试

---

## 8. 归档摘要

- **2026-07-04**：Bug 修复（信号参数覆盖闭包变量 → 点击卡片崩溃）+ 预览弹窗滚动优化（摘要+讨论引导合并滚动区）+ 文章正文提取（article_extractor.py 从原文 URL 抓取完整内容供 LLM 深度摘要）+ 加载动画（选角色后转圈等待 + 30 秒超时降级预设话题）。新增 1 个文件，修改 2 个文件。168 测试全过。

- **2026-07-03**：中文 RSS 信息源 + 每日持久化缓存 + AI 内容筛选 + 话题预览弹窗。8 类 18 个中文源替代全部英文源；RssCacheManager 磁盘缓存按日期刷新；Cloud 模式 LLM 五维度审核话题，Mock 模式规则过滤；TopicPreviewDialog 展示 AI 中文摘要和英语讨论引导。168 测试全过。下一步：ConversationManager 接入 ChatPage，音标数据补齐。

- **2026-07-01**：VocaLand v2 升级完成。新增用户系统、QStackedWidget 四页面导航、话题生成器、墨墨式闪卡复习、取词弹窗和自适应 Prompt。168 测试全过。
