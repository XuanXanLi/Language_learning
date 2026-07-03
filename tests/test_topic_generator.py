"""TopicGenerator 测试。

覆盖：fallback 话题生成、兴趣匹配、安全过滤。
"""

import pytest

from line_c.engine.topic_generator import TopicGenerator, TopicCard, BLOCKED_KEYWORDS


class TestFallbackTopics:
    def test_generates_topics_without_llm(self):
        gen = TopicGenerator(llm=None)
        topics = gen.generate(["ai_tech", "finance"], "middle", count=6)
        assert len(topics) >= 3
        assert all(isinstance(t, TopicCard) for t in topics)
        assert all(t.source == "预设" for t in topics)

    def test_generates_generic_when_no_interests_match(self):
        gen = TopicGenerator(llm=None)
        topics = gen.generate(["custom_interest"], "middle", count=4)
        assert len(topics) >= 3
        assert all(t.title for t in topics)
        assert all(t.summary for t in topics)

    def test_each_topic_has_title_and_summary(self):
        gen = TopicGenerator(llm=None)
        topics = gen.generate(["ai_tech"], "middle")
        for t in topics:
            assert t.title
            assert t.summary

    def test_respects_count(self):
        gen = TopicGenerator(llm=None)
        topics = gen.generate(["travel", "music", "sports"], "middle", count=4)
        assert len(topics) <= 8  # max 8 cap


class TestSafetyFilter:
    def test_blocks_political_content(self):
        gen = TopicGenerator(llm=None)
        topics = [
            TopicCard(title="Election Politics", summary="About the president party"),
            TopicCard(title="Travel to Japan", summary="Exploring beautiful places"),
        ]
        filtered = gen._safety_filter(topics)
        assert len(filtered) == 1
        assert filtered[0].title == "Travel to Japan"

    def test_blocks_violence_content(self):
        gen = TopicGenerator(llm=None)
        topics = [
            TopicCard(title="War Stories", summary="About military weapons and kill"),
        ]
        filtered = gen._safety_filter(topics)
        assert len(filtered) == 0

    def test_allows_educational_content(self):
        gen = TopicGenerator(llm=None)
        topics = [
            TopicCard(title="Learn AI", summary="Machine learning and neural networks"),
            TopicCard(title="Cooking Tips", summary="How to make delicious food"),
        ]
        filtered = gen._safety_filter(topics)
        assert len(filtered) == 2


class TestBlockedKeywords:
    def test_blocked_keywords_cover_main_categories(self):
        """确保安全关键词覆盖主要违规类别。"""
        categories = {
            "politics": ["politics", "election", "president"],
            "violence": ["violence", "kill", "war"],
            "adult": ["adult", "sexual", "porn"],
        }
        for category, keywords in categories.items():
            for kw in keywords:
                assert kw in BLOCKED_KEYWORDS, f"'{kw}' should be in BLOCKED_KEYWORDS"
