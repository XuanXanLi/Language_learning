# VocaLand v2 全自动实施日志
> 开始时间: 2026-06-30
> 完成时间: 2026-07-01
> 模式: 全自动 (User asleep)
> 策略: 按Phase顺序实施，每Phase完成跑全量测试
> 最终结果: ✅ 168/168 测试通过，零失败

---

## 完成摘要

### Phase 0: 数据层 ✅
- 3 个 domain 数据类: UserProfile, ChatSession, UserVocabulary (+VocabState)
- 3 个 repository: UserRepository, ChatSessionRepository, UserVocabularyRepository
- 3 张新 SQLite 表: user_profile, chat_session, user_vocabulary
- 33 个新测试全部通过

### Phase 1: 导航框架 + 首页 ✅
- main_window.py 重写为 QStackedWidget 导航壳 (4 个页面)
- home_page.py: 角色卡片列表 + 创建/编辑/删除弹窗 + 水平/兴趣气泡
- topic_feed_page.py: 话题卡片列表 + 自定义输入 + 复习入口
- chat_page.py: 两栏布局 + _TappableBubble + 生词面板
- review_page.py: 墨墨式闪卡复习 + SM-2 自评
- main.py 重写，注入所有依赖

### Phase 2: 话题生成 ✅
- topic_generator.py: LLM 驱动 + hardcoded fallback (每个兴趣领域 3 个话题)
- 安全过滤: 阻止政治/暴力/成人内容关键词
- 8 个测试通过

### Phase 3: 聊天核心 ✅
- _TappableBubble: QTextEdit 取词 + word_clicked 信号
- WordPopup: 查词弹窗 (本地DB → CloudLLM → 兜底)
- ChatPage: 真实 LLM 对话 + 即时生词保存 + 去抖发送
- 自适应 Prompt: 根据角色英语水平调整 persona (5 档)

### Phase 4: 复习系统 ✅
- ReviewSessionManager: SM-2 评分 + 掌握判定 + 抽查
- ReviewPage: 正面/背面翻转 + 三按钮自评 + 完成统计
- 10 个测试通过

### Phase 5: 集成 ✅
- 迁移脚本 v2_migration.py: 备份 → 建表 → 验证
- TopicGenerator 注入 TopicFeedPage
- 全量 QA: 168/168 测试通过

## 文件变更清单

### 新建 (16 个文件)
- src/line_c/domain/user_profile.py
- src/line_c/domain/chat_session.py
- src/line_c/domain/user_vocabulary.py
- src/line_c/engine/user_repository.py
- src/line_c/engine/chat_session_repository.py
- src/line_c/engine/user_vocabulary_repository.py
- src/line_c/engine/topic_generator.py
- src/line_c/engine/review_session_manager.py
- src/line_c/ui/pages/__init__.py
- src/line_c/ui/pages/home_page.py
- src/line_c/ui/pages/topic_feed_page.py
- src/line_c/ui/pages/chat_page.py
- src/line_c/ui/pages/review_page.py
- src/line_c/ui/widgets/__init__.py
- src/line_c/ui/widgets/word_popup.py
- scripts/v2_migration.py

### 新建测试 (5 个文件, 51 个测试)
- tests/test_user_repository.py (10 测试)
- tests/test_chat_session_repository.py (7 测试)
- tests/test_user_vocabulary_repository.py (16 测试)
- tests/test_topic_generator.py (8 测试)
- tests/test_review_session_manager.py (10 测试)

### 修改 (2 个文件)
- src/line_c/ui/main_window.py (重写为 QStackedWidget 导航壳)
- src/main.py (重写为 v2 入口)

### 未修改 (旧功能保持完好)
- domain/word.py, domain/vocabulary_state.py, domain/learning_event.py
- domain/learning_record.py
- engine/vocabulary_repository.py (旧表 + 旧逻辑不变)
- engine/conversation_manager.py (旧逻辑不变，后续 Phase 可迁移)
- engine/prompt_builder.py (旧逻辑不变)
- engine/sm2_srs.py, engine/srs_scheduler.py
- engine/learning_evaluator.py, engine/mastery_scorer.py
- engine/state_machine.py, engine/target_word_tracker.py
- llm/base.py, llm/mock_llm.py, llm/cloud_llm.py
- tts/base.py, tts/mock_tts.py
- ui/character_widget.py, ui/status_indicator.py
- 所有旧测试文件

## 已知限制

1. ChatPage 直接使用 LLM 而非 ConversationManager（简化版，后续可迁移）
2. 音标未在取词弹窗中从 DB 获取（需要 WordPopup._lookup 增加 phonetic 字段提取）
3. 复习页卡片翻转时音标未从 DB 获取（目前查 DB 仅获取释义）
4. 触屏适配未做（但 mousePressEvent 同时响应触屏和鼠标）
5. RSS 新闻源未接入（当前为 LLM 生成 + fallback 话题）

## 下一步

1. `python3 src/main.py --llm mock` 启动应用验证 UI 交互
2. CloudLLM 模式下测试真实话题生成
3. 根据需要决定是否迁移 ConversationManager
4. 触屏硬件到位后验证取词体验

