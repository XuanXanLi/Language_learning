#!/usr/bin/env python3
"""VocaAI 风格引擎演示 —— 展示新的对话驱动词汇学习流程。"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from line_c.domain.word import Word
from line_c.engine.vocabulary_repository import VocabularyRepository
from line_c.engine.conversation_manager import ConversationManager, STOP_WORDS
from line_c.engine.prompt_builder import PromptBuilder
from line_c.llm.mock_llm import MockLLM


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── 构建测试环境 ──
repo = VocabularyRepository(Path(":memory:"))
test_words = [
    Word(word="curious", phonetic="/t/", part_of_speech="adj.",
         definition_en="eager to know", definition_cn="好奇的",
         examples=[], level="cet4", topic_tags=["emotion"], difficulty=0.3),
    Word(word="discover", phonetic="/t/", part_of_speech="v.",
         definition_en="find something new", definition_cn="发现",
         examples=[], level="cet4", topic_tags=["education"], difficulty=0.3),
    Word(word="explore", phonetic="/t/", part_of_speech="v.",
         definition_en="travel to discover", definition_cn="探索",
         examples=[], level="cet4", topic_tags=["travel"], difficulty=0.3),
    Word(word="energetic", phonetic="/t/", part_of_speech="adj.",
         definition_en="full of energy", definition_cn="精力充沛的",
         examples=[], level="cet4", topic_tags=["health"], difficulty=0.3),
    Word(word="hiking", phonetic="/t/", part_of_speech="n.",
         definition_en="walking in nature", definition_cn="徒步旅行",
         examples=[], level="cet4", topic_tags=["travel"], difficulty=0.3),
    Word(word="endurance", phonetic="/t/", part_of_speech="n.",
         definition_en="ability to endure", definition_cn="耐力",
         examples=[], level="cet6", topic_tags=["health"], difficulty=0.5),
    Word(word="trail", phonetic="/t/", part_of_speech="n.",
         definition_en="a path through countryside", definition_cn="小径；路线",
         examples=[], level="cet4", topic_tags=["travel"], difficulty=0.2),
]
repo.add_words(test_words)

# ── 演示1：词提取 + 停用词过滤 ──
section("演示1：从对话中提取 CET 词汇")

# 创建一个临时 manager 用于演示（不连接 Qt 信号）
from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
llm = MockLLM()
mgr = ConversationManager(llm=llm, repository=repo)

sentences = [
    ("用户", "I went hiking yesterday, it was amazing!"),
    ("用户", "The trail was beautiful and I felt energetic."),
    ("LLM", "Hiking builds endurance and helps you discover nature."),
]

for speaker, text in sentences:
    words = mgr._extract_words(text)
    lookup = mgr._batch_lookup(words)
    cet_words = [w for w, s in lookup.items() if s != "N/A"]
    print(f"\n{speaker}: \"{text}\"")
    print(f"  提取词: {words}")
    print(f"  命中 CET 词库: {cet_words}")


# ── 演示2：完整对话模拟 ──
section("演示2：完整对话模拟（VocaAI 风格）")

mgr.start_session(topic="travel")

conversation = [
    ("用户", "What do you like to do on weekends?"),
    ("LLM", "I love to explore new hiking trails. It makes me feel energetic!"),
    ("用户", "Oh I enjoy hiking too. I want to discover more trails near my city."),
    ("LLM", "That's the spirit! Being curious about nature is wonderful."),
    ("用户", "Yeah I'm curious about mountain hiking. But I need more endurance."),
]

for i, (speaker, text) in enumerate(conversation):
    if speaker == "用户":
        print(f"\n[轮次 {i//2+1}] 用户: \"{text}\"")
        mgr.handle_user_message(text)
    else:
        print(f"[轮次 {i//2+1}] LLM:  \"{text}\"")
        # 模拟 LLM 回复（不实际发 LLM 请求，直接调用扫描）
        mgr._scan_message(text, speaker="llm")


# ── 结果 ──
print(f"\n{'─'*60}")
print("会话结束后的词汇追踪：")
summary = mgr.get_session_summary()
print(f"  话题: {summary['topic']}")
print(f"  轮数: {summary['turns']}")
print(f"  LLM 引入的词（用户见过）: {summary['words_seen']}")
print(f"  用户用过的词: {summary['words_used']}")
print(f"  薄弱词: {summary['weak_words']}")

print(f"\n数据库状态：")
for word in test_words:
    state = mgr._get_db_state(word.word)
    print(f"  {word.word:12} → {state}")

# ── 演示3：Prompt 对比 ──
section("演示3：新 Prompt 风格（无目标词，话题驱动）")

builder = PromptBuilder()
prompt = builder.build(
    recent_words=["hiking", "energetic", "explore", "trail"],
    preferred_topic="travel",
)
print(prompt[:500])
print("...")

print(f"\n{'='*60}")
print("演示结束。核心变化总结：")
print("  旧：'今天要教这3个词' → 强制塞入 Prompt → 只追踪这3个")
print("  新：'聊旅行话题' → 自然对话 → 后台扫描所有 CET 词汇")
print(f"{'='*60}")

repo.close()
