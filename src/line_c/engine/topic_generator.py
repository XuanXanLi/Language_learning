"""话题生成器。

基于用户兴趣生成英文学习对话话题。
优先级: CloudLLM → 内置 fallback 话题。
安全过滤: 拒绝政治/暴力/成人内容。
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .article_extractor import fetch_and_extract


@dataclass
class TopicCard:
    """一个话题摘要卡片。"""
    title: str = ""
    summary: str = ""        # 中文摘要（从 RSS 源直接获取）
    summary_cn: str = ""     # 备用：AI 翻译的中文摘要（已弃用，保留向后兼容）
    source: str = "AI生成"    # "📰 RSS源名" / "AI生成" / "预设"
    approved: bool = True       # AI 筛选是否通过
    approval_reason: str = ""
    source_url: str = ""        # RSS 原文链接（供预览页 AI 摘要用）
    discussion_guide: List[str] = field(default_factory=list)  # 英语讨论引导问题


# ── 安全关键词（出现则拒绝该话题）──
BLOCKED_KEYWORDS = [
    # 英文敏感词（保留，兼容英文内容）
    "politics", "political", "election", "president", "party",
    "violence", "kill", "murder", "weapon", "war", "terrorist",
    "adult", "porn", "sexual", "nude", "explicit", "sex",
    "drug", "cocaine", "heroin",
    "suicide", "self-harm",
    # 中文敏感词
    "政治", "选举", "总统", "党派", "示威", "抗议",
    "暴力", "谋杀", "武器", "战争", "恐怖",
    "成人", "色情", "裸体", "性爱", "艳照",
    "毒品", "可卡因", "海洛因", "吸毒",
    "自杀", "自残", "抑郁",
]

# ── 内置 fallback 话题（按兴趣领域）──
FALLBACK_TOPICS: dict[str, List[dict]] = {
    "ai_tech": [
        {"title": "AI如何改变我们的工作方式",
         "summary": "从自动化到智能助手，AI正在重塑各行各业。一起讨论AI对你生活的影响。"},
        {"title": "开源大模型 vs 闭源API",
         "summary": "2026年的AI格局发生了巨大变化，开源模型的能力越来越强。"},
        {"title": "智能设备让生活更便捷",
         "summary": "从智能家居到可穿戴设备，科技如何改变我们的日常习惯。"},
    ],
    "finance": [
        {"title": "数字货币与未来支付",
         "summary": "各国央行数字货币正在加速推出，这对我们的日常生活意味着什么？"},
        {"title": "年轻人如何开始理财",
         "summary": "从储蓄到投资，每个人的财务自由之路从哪里开始。"},
        {"title": "全球经济趋势观察",
         "summary": "利率变化、就业市场和产业转移——当前经济的关键话题。"},
    ],
    "science": [
        {"title": "太空探索新纪元",
         "summary": "私人航天公司和国家级任务正在将人类推向更远的宇宙。"},
        {"title": "基因编辑的伦理与未来",
         "summary": "CRISPR技术的突破带来了治疗遗传疾病的希望，也引发了伦理思考。"},
        {"title": "气候变化与清洁能源",
         "summary": "太阳能、风能和核聚变——哪些清洁能源最有前景？"},
    ],
    "history": [
        {"title": "古代文明的有趣发现",
         "summary": "考古学家不断发现新的线索，改写我们对古代文明的理解。"},
        {"title": "丝绸之路上的文化交流",
         "summary": "千年之前的贸易路线如何塑造了今天的文化格局。"},
    ],
    "travel": [
        {"title": "最值得去的冷门目的地",
         "summary": "避开游客人群，探索那些鲜为人知但同样美丽的地方。"},
        {"title": "美食之旅：用味蕾探索世界",
         "summary": "从街头小吃到米其林餐厅，美食是了解一个文化的窗口。"},
        {"title": "独自旅行的乐趣与挑战",
         "summary": "一个人上路，遇见自己，也遇见世界。"},
    ],
    "music": [
        {"title": "流媒体如何改变音乐产业",
         "summary": "从唱片到Spotify，音乐消费方式的革命。"},
        {"title": "音乐与情绪的科学",
         "summary": "为什么某些歌曲能触动我们？音乐如何影响大脑和情绪？"},
    ],
    "sports": [
        {"title": "体育精神：比胜负更重要的东西",
         "summary": "从奥运会到社区运动会，体育教会我们什么？"},
        {"title": "电子竞技的崛起",
         "summary": "电竞已经成为全球数亿人的娱乐和职业选择。"},
    ],
    "games": [
        {"title": "游戏设计的艺术",
         "summary": "是什么让一款游戏让人欲罢不能？探讨游戏设计的核心要素。"},
        {"title": "独立游戏的黄金时代",
         "summary": "小团队如何创造出全球畅销的游戏作品？"},
    ],
}

# 通用话题（当没有匹配的兴趣时使用）
GENERIC_TOPICS = [
    {"title": "学习新语言的乐趣",
     "summary": "掌握一门外语能打开新世界的大门。分享你的语言学习经历。"},
    {"title": "难忘的生活经历",
     "summary": "每个人都有独特的故事。讲述那些让你成长的重要时刻。"},
    {"title": "未来的职业规划",
     "summary": "在快速变化的世界中，如何规划自己的职业道路？"},
    {"title": "友谊的意义",
     "summary": "什么是真正的朋友？分享友谊如何丰富了你的生活。"},
    {"title": "环保从小事做起",
     "summary": "日常生活中的小决定如何影响地球的未来。"},
    {"title": "读书的快乐",
     "summary": "最近读了什么好书？分享你的阅读体验和推荐。"},
]


class TopicGenerator:
    """根据用户兴趣生成英文学习话题。

    优先级: RSS新闻 → LLM生成 → 内置fallback
    """

    def __init__(self, llm=None, rss_fetcher=None):
        """llm: CloudLLM 实例。rss_fetcher: RSSFeedFetcher 实例。"""
        self.llm = llm
        self.rss = rss_fetcher

    def generate(
        self, interests: List[str], english_level: str = "middle", count: int = 6
    ) -> List[TopicCard]:
        """生成话题卡片列表。

        1. RSS 新闻（优先） → AI 筛选（cloud 模式）或规则筛选（mock 模式）
        2. LLM 生成（RSS 不可用时）
        3. 内置 fallback（最后兜底）
        4. 安全过滤
        """
        topics = []

        # 1. RSS 真实新闻
        if self.rss:
            try:
                rss_topics = self.rss.fetch(interests, count=count)
                if rss_topics:
                    # AI 筛选（cloud 模式）或规则筛选（mock 模式）
                    if self.llm:
                        try:
                            rss_topics = self.rss.filter_with_llm(rss_topics, self.llm)
                        except Exception:
                            pass  # LLM 筛选失败，用全部
                    else:
                        rss_topics = self.rss.basic_relevance_filter(rss_topics)
                    topics = rss_topics
            except Exception:
                pass

        # RSS 有结果 → 安全过滤直接返回
        if topics:
            return self._safety_filter(topics)[:8]

        # 2. LLM 生成
        if self.llm:
            try:
                llm_topics = self._generate_with_llm(interests, english_level, count)
                if llm_topics:
                    topics = llm_topics
            except Exception:
                pass  # LLM 失败，用 fallback

        # LLM 生成失败或未配置 → fallback
        if not topics:
            topics = self._generate_fallback(interests, count)

        # 安全过滤
        topics = self._safety_filter(topics)

        return topics[:8]  # 最多 8 个

    def _generate_with_llm(
        self, interests: List[str], level: str, count: int
    ) -> List[TopicCard]:
        """调用 LLM 生成话题。"""
        interest_str = ", ".join(interests)
        level_str = {
            "beginner": "beginner (very simple English)",
            "primary": "elementary",
            "middle": "intermediate",
            "high": "upper-intermediate",
            "advanced": "advanced",
        }.get(level, "intermediate")

        prompt = f"""Generate {count} English conversation topics for a language learner.

The learner is interested in: {interest_str}.
Their English level is: {level_str}.

Each topic should:
- Be a conversation starter that makes the learner want to talk
- Have a catchy title (max 10 words, in the learner's native language style)
- Have a 2-3 sentence summary (in English, max 80 words total)
- Be appropriate for an educational conversation
- NOT include politics, violence, adult content, or illegal topics

Return ONLY a JSON array with this format:
[{{"title": "...", "summary": "..."}}, ...]

Do NOT include any text before or after the JSON. Return ONLY the JSON array."""

        response = self.llm.chat(
            system_prompt="You generate safe, educational English conversation topics. Output pure JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )

        if not response or not response.text:
            return []

        # 解析 JSON
        import json
        text = response.text.strip()
        # 去掉可能的 markdown 代码块标记
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]

        try:
            items = json.loads(text)
            return [
                TopicCard(
                    title=item.get("title", ""),
                    summary=item.get("summary", ""),
                    source="AI生成",
                )
                for item in items
                if item.get("title")
            ]
        except json.JSONDecodeError:
            return []

    def _generate_fallback(
        self, interests: List[str], count: int
    ) -> List[TopicCard]:
        """从内置 fallback 话题中选取。"""
        result = []
        seen_titles = set()

        # 先从匹配的兴趣领域选取
        for interest in interests:
            if interest in FALLBACK_TOPICS:
                for topic in FALLBACK_TOPICS[interest]:
                    if topic["title"] not in seen_titles:
                        result.append(TopicCard(**topic, source="预设"))
                        seen_titles.add(topic["title"])
                        if len(result) >= count:
                            return result

        # 不足则补充通用话题
        for topic in GENERIC_TOPICS:
            if topic["title"] not in seen_titles:
                result.append(TopicCard(**topic, source="预设"))
                seen_titles.add(topic["title"])
                if len(result) >= count:
                    return result

        return result

    def generate_preview(self, topic: TopicCard) -> TopicCard:
        """为话题生成预览内容：AI 中文摘要 + 英语讨论引导问题。

        Cloud 模式：调 LLM 生成。
        Mock 模式：模板生成。
        结果写回 topic.discussion_guide，同时 topic.summary 保持不变。
        """
        if self.llm:
            try:
                return self._generate_preview_with_llm(topic)
            except Exception:
                pass  # LLM 失败 → 用模板

        return self._generate_preview_template(topic)

    def _generate_preview_with_llm(self, topic: TopicCard) -> TopicCard:
        """调 LLM 生成中文摘要 + 英语讨论引导。

        优先从原文 URL 抓取完整文章内容；抓取失败则用 RSS 摘要。
        """
        # 尝试抓取原文正文（带短超时，不影响主流程）
        article_text = ""
        if topic.source_url:
            try:
                fetched = fetch_and_extract(topic.source_url, timeout=6)
                if fetched and len(fetched) > 50:
                    article_text = fetched[:2500]  # 截断，控制 token 消耗
            except Exception:
                pass

        # 构建 prompt
        if article_text:
            content_block = f"文章原文（节选）:\n{article_text}"
        else:
            content_block = f"话题摘要: {topic.summary}"

        prompt = f"""你是一位英语学习内容编辑。用户选了一个话题，你需要生成预览内容。

话题标题: {topic.title}
{content_block}

请生成两部分内容：

1. **中文摘要**（约200-300字）：帮用户快速了解这个新闻在说什么。基于原文内容撰写，信息丰富有深度。
2. **英语讨论引导**（3-5个问题）：围绕文章核心内容，适合中级英语学习者，能用简单英语回答的开放式问题。

返回纯 JSON：
{{"summary_cn": "中文摘要内容...", "questions": ["What do you think about...", "Have you ever...", "Do you believe..."]}}

不要返回 JSON 以外的任何文字。"""

        resp = self.llm.chat(
            system_prompt="你是英语学习内容编辑，输出纯 JSON。",
            messages=[{"role": "user", "content": prompt}],
        )
        if not resp or not resp.text:
            return topic

        import json
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]

        try:
            data = json.loads(text)
            topic.summary_cn = data.get("summary_cn", "")
            topic.discussion_guide = data.get("questions", [])
        except json.JSONDecodeError:
            pass

        return topic

    def _generate_preview_template(self, topic: TopicCard) -> TopicCard:
        """模板生成讨论引导（Mock 模式）。"""
        title = str(topic.title)
        template_questions = [
            f"What do you know about {title[:20]}?",
            "What's your opinion on this topic?",
            "Have you had any personal experience related to this?",
            "How does this affect people's daily lives?",
        ]
        topic.discussion_guide = template_questions
        topic.summary_cn = str(topic.summary)
        return topic

    def _safety_filter(self, topics: List[TopicCard]) -> List[TopicCard]:
        """过滤不安全话题。"""
        filtered = []
        for topic in topics:
            text = f"{topic.title} {topic.summary}".lower()
            blocked = any(kw in text for kw in BLOCKED_KEYWORDS)
            if not blocked:
                filtered.append(topic)
        return filtered
