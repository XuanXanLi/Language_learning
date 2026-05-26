"""LLM 适配器的抽象基类。

整个项目通过这个接口与 LLM 对话。换 LLM 后端
（Mock → Cloud → Ollama → RKLLM）不需要改业务代码。

抽象基类（ABC, Abstract Base Class）：定义方法的签名，
但不能直接实例化。子类必须实现这些方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LLMResponse:
    """LLM 的一次回复。

    dataclass 自动生成 __init__，你只需要声明字段和类型。
    """
    text: str                         # 回复文本
    latency_ms: float = 0.0           # 从发请求到收到回复的耗时（毫秒）
    tokens_used: int = 0              # 消耗的 token 数（用于统计）
    target_words_used: List[str] = field(default_factory=list)
    # ↑ LLM 在回复中使用了哪些目标词汇


class BaseLLM(ABC):
    """LLM 抽象基类——所有 LLM 后端的统一接口。

    子类必须实现：
    - chat(): 发送对话请求，返回回复
    - is_available(): 检查后端是否可用
    """

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        messages: List[dict],
    ) -> LLMResponse:
        """发送对话请求。

        参数：
        - system_prompt: 系统提示词（角色设定等不变内容）
        - messages:     对话历史，格式 [{"role": "user", "content": "..."}, ...]

        返回：
        - LLMResponse: 包含回复文本和元信息
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检测 LLM 后端是否可用。

        MockLLM 永远返回 True，
        Cloud/Ollama 会实际检测网络/服务是否可达。
        """
        ...

    @property
    def name(self) -> str:
        """后端名称，方便日志输出。"""
        return self.__class__.__name__
