"""Prompt 构建器。

核心理念：用户说中文词 → LLM 先翻译再回答 → 系统追踪英文对应词。

Prompt 结构：
  1. 系统层 — 角色设定 + 对话规则 + 用户等级
  2. 中文焦点层 — 用户刚说的中文词（告诉 LLM 先翻译再回答）
  3. 会话层 — 最近出现的英文 CET 词汇 + 薄弱词
"""

from typing import List, Optional


SYSTEM_PROMPT_TEMPLATE = """You are {persona_name}, a friendly English-speaking companion. \
You chat naturally with the user about everyday topics — like a friend, not a teacher.

## Conversation Topic
{preferred_topic}

## About Your Conversation Partner
- English level: {cefr_level} (approximately {vocab_size} words known)
- Native language: Chinese (may code-switch occasionally)

## Your Personality
- Speak naturally, like chatting over coffee. Do NOT sound like a textbook.
- Be warm, encouraging, and occasionally playful.
- Keep responses under {max_words} words.
- Ask follow-up questions to keep the conversation flowing.

## Important Rules
1. **ALWAYS respond in English.** Even if the user writes entirely in Chinese, you must reply in English. This is an English learning tool — you are the user's only English-speaking partner.
2. Use vocabulary appropriate for {cefr_level} level — not too simple, not too hard.
3. If the user uses a word incorrectly, gently model the correct usage — don't lecture.
4. If the user seems confused by a word, explain it in a natural way ("Oh, by X I mean...").
5. If the user asks about a word directly (e.g. "what does X mean?"), explain it clearly with an example.
{chinese_focus_section}
{recent_words_section}
{weak_words_section}
Be a good conversation partner. The learning happens naturally — you don't need to force it."""


def _build_chinese_focus_section(words: Optional[List[str]]) -> str:
    """生成"中文焦点词"段落——用户用中文问的词，LLM 必须完整复述再回答。"""
    if not words:
        return ""
    word_list = "、".join(words)
    return (
        f"## Chinese Words Your Partner Just Used\n"
        f"Your partner used these Chinese words: {word_list}.\n"
        f"CRITICAL: First, restate your partner's ENTIRE message naturally in English — "
        f"make sure EVERY Chinese word above gets translated. "
        f"Then respond to what they said. "
        f"Do NOT skip any Chinese word. If there are 3 Chinese words, all 3 must appear in your English restatement.\n"
    )


def _build_recent_words_section(words: Optional[List[str]]) -> str:
    """生成"最近遇到过的词"段落，让 LLM 自然回抛。"""
    if not words:
        return ""
    word_list = ", ".join(words[:10])
    return (
        f"## Words Your Partner Has Recently Encountered\n"
        f"When it feels natural, try to weave one or two of these into the conversation: "
        f"{word_list}. Don't force it — only use them if they fit naturally.\n"
    )


def _build_weak_words_section(words: Optional[List[str]]) -> str:
    """生成"薄弱词"段落，让 LLM 关注这些词。"""
    if not words:
        return ""
    word_list = ", ".join(words[:5])
    return (
        f"## Words Your Partner Struggles With\n"
        f"These words have come up before but haven't been used much: "
        f"{word_list}. If a natural chance comes up, try using one of them.\n"
    )


DEFAULT_CONFIG = {
    "persona_name": "Leo",
    "cefr_level": "CET-4",
    "vocab_size": "about 2000",
    "max_words": 50,
    "preferred_topic": "daily life",
}


class PromptBuilder:
    """构建自然对话风格的 LLM 提示词。

    用法：
        builder = PromptBuilder()
        prompt = builder.build(recent_words=["curious", "hiking", "energetic"])
    """

    def __init__(self, **kwargs):
        self.config = {**DEFAULT_CONFIG, **kwargs}

    def build(
        self,
        recent_words: Optional[List[str]] = None,
        weak_words: Optional[List[str]] = None,
        chinese_words: Optional[List[str]] = None,
        **overrides,
    ) -> str:
        """构建系统提示词。

        参数：
        - chinese_words: 用户刚用的中文词（告诉 LLM 先翻译再回答）
        - recent_words:  用户最近在对话中遇到过的 CET 词汇（用于自然回抛）
        - weak_words:    用户见过但一直没主动用过的词（需要强化）
        - **overrides:   临时覆盖配置（如 preferred_topic="travel"）
        """
        config = {**self.config, **overrides}

        # 构建动态段落
        chinese_section = _build_chinese_focus_section(chinese_words)
        recent_section = _build_recent_words_section(recent_words)
        weak_section = _build_weak_words_section(weak_words)

        return SYSTEM_PROMPT_TEMPLATE.format(
            persona_name=config["persona_name"],
            cefr_level=config["cefr_level"],
            vocab_size=config["vocab_size"],
            max_words=config["max_words"],
            preferred_topic=config["preferred_topic"],
            chinese_focus_section=chinese_section,
            recent_words_section=recent_section,
            weak_words_section=weak_section,
        )

    def build_session_context(
        self,
        recent_words: Optional[List[str]] = None,
        chinese_words: Optional[List[str]] = None,
        turns_this_session: int = 0,
    ) -> str:
        """生成会话级上下文（追加在系统 Prompt 后面）。"""
        parts = []
        if chinese_words:
            parts.append(
                f"Remember: your partner used Chinese words ({', '.join(chinese_words)}). "
                f"First restate their question in natural English, then answer."
            )
        if recent_words and turns_this_session >= 3:
            parts.append(
                f"Your partner has encountered these words recently: "
                f"{', '.join(recent_words[:8])}. "
                f"Consider naturally bringing one back into the conversation."
            )
        return "\n".join(parts)
