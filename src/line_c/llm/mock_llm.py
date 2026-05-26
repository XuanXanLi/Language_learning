"""MockLLM：返回固定回复的假 LLM。

用于开发阶段，不需要网络、不需要模型、零依赖。
可以预设一个回复列表，按顺序返回。
"""

from typing import List

from .base import BaseLLM, LLMResponse


class MockLLM(BaseLLM):
    """返回预设回复的模拟 LLM。

    用法：
        llm = MockLLM(responses=["Hello!", "Nice to meet you!"])
        r1 = llm.chat("...", [...])  # → "Hello!"
        r2 = llm.chat("...", [...])  # → "Nice to meet you!"
        r3 = llm.chat("...", [...])  # → 循环回 "Hello!"

    这个类让你在没有模型、没有网络的情况下，
    把整套对话逻辑跑通。相当于排练时用的提词板。
    """

    def __init__(self, responses: List[str] | None = None):
        """
        responses: 预设的回复列表。传 None 则使用默认回复。
        """
        self._responses = responses or [
            "That's interesting! Tell me more about it.",
            "I see what you mean. By the way, have you heard of the word 'curious'? It means wanting to know more about something.",
            "Let me share a thought: it's important to be patient when learning new things.",
            "That reminds me of something — 'discover' is a great word. It means to find something new.",
            "I agree! Speaking of which, can you try using 'explore' in a sentence?",
        ]
        self._index = 0           # 当前回复的索引
        self._call_count = 0      # 总调用次数（调试用）

    def chat(
        self,
        system_prompt: str,
        messages: List[dict],
    ) -> LLMResponse:
        """返回预设列表中的下一条回复。循环使用。"""
        response_text = self._responses[self._index % len(self._responses)]
        self._index += 1
        self._call_count += 1

        return LLMResponse(
            text=response_text,
            latency_ms=0.0,       # Mock 零延迟
            tokens_used=len(response_text.split()),
        )

    def is_available(self) -> bool:
        """MockLLM 永远可用。"""
        return True

    @property
    def call_count(self) -> int:
        """查看已经被调用了几次。"""
        return self._call_count
