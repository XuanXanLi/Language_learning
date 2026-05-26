"""Prompt 构建器测试（VocaAI 风格）。

验证：
- 基础系统 Prompt 包含话题和等级
- 最近遇到的词出现在 Prompt 中
- 薄弱词出现在 Prompt 中
- 没有目标词概念
- 会话上下文在足够轮数后包含最近词
"""
from line_c.engine.prompt_builder import PromptBuilder


class TestPromptBuilder:

    def test_basic_prompt_contains_topic(self):
        builder = PromptBuilder()
        prompt = builder.build(preferred_topic="travel")
        assert "travel" in prompt

    def test_basic_prompt_contains_level(self):
        builder = PromptBuilder()
        prompt = builder.build()
        assert "CET-4" in prompt

    def test_basic_prompt_contains_persona(self):
        builder = PromptBuilder()
        prompt = builder.build()
        assert "Leo" in prompt

    def test_no_target_words_section(self):
        """VocaAI 风格的 Prompt 不应该有 'target words' 概念。"""
        builder = PromptBuilder()
        prompt = builder.build()
        assert "target words" not in prompt.lower()
        assert "Today's Learning Goals" not in prompt

    def test_recent_words_appear(self):
        """最近遇到的词应该出现在 Prompt 中。"""
        builder = PromptBuilder()
        prompt = builder.build(recent_words=["curious", "discover", "explore"])
        assert "curious" in prompt
        assert "discover" in prompt
        assert "explore" in prompt
        # 应该说明这是"最近遇到过的词"
        assert "Recently Encountered" in prompt

    def test_no_recent_words_shows_no_section(self):
        """没有最近遇到的词时，不显示该段落。"""
        builder = PromptBuilder()
        prompt = builder.build(recent_words=None)
        assert "Recently Encountered" not in prompt

    def test_weak_words_appear(self):
        """薄弱词应该出现在 Prompt 中。"""
        builder = PromptBuilder()
        prompt = builder.build(weak_words=["abandon", "struggle"])
        assert "abandon" in prompt
        assert "struggle" in prompt
        assert "Struggles With" in prompt

    def test_no_weak_words_shows_no_section(self):
        """没有薄弱词时，不显示该段落。"""
        builder = PromptBuilder()
        prompt = builder.build(weak_words=None)
        assert "Struggles With" not in prompt

    def test_custom_persona(self):
        builder = PromptBuilder(persona_name="Lily")
        prompt = builder.build()
        assert "Lily" in prompt
        assert "Leo" not in prompt

    def test_custom_level(self):
        builder = PromptBuilder()
        prompt = builder.build(cefr_level="CET-6")
        assert "CET-6" in prompt

    def test_topic_override_in_build(self):
        builder = PromptBuilder()
        prompt = builder.build(preferred_topic="technology")
        assert "technology" in prompt.lower()

    def test_session_context_before_3_turns(self):
        """不足 3 轮时，会话上下文为空。"""
        builder = PromptBuilder()
        ctx = builder.build_session_context(
            recent_words=["curious"], turns_this_session=1
        )
        assert ctx == ""

    def test_session_context_after_3_turns(self):
        """3 轮以上时，会话上下文提醒回抛。"""
        builder = PromptBuilder()
        ctx = builder.build_session_context(
            recent_words=["curious", "discover"], turns_this_session=4
        )
        assert "curious" in ctx
        assert "discover" in ctx

    def test_max_words_in_prompt(self):
        builder = PromptBuilder()
        prompt = builder.build(max_words=60)
        assert "60" in prompt
