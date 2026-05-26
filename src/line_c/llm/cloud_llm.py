"""CloudLLM：通过 HTTP 调用云端 LLM API。

支持任何 OpenAI 兼容接口（DeepSeek、通义千问、OpenAI 等）。
配置在 config.py 中：CLOUD_API_URL 和 CLOUD_API_KEY。
"""

import json
import time
from typing import List, Optional

import requests

from .base import BaseLLM, LLMResponse


class CloudLLM(BaseLLM):
    """通过 HTTP 调用云端大模型 API。

    用法：
        llm = CloudLLM(
            api_url="https://api.deepseek.com/v1/chat/completions",
            api_key="sk-xxxx",
            model="deepseek-chat",
        )
        response = llm.chat(system_prompt, messages)
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str = "deepseek-chat",
        max_tokens: int = 150,
        temperature: float = 0.7,
    ):
        """
        参数说明：
        - api_url:      API 地址
        - api_key:      API 密钥（从服务商获取）
        - model:        模型名称
        - max_tokens:   每次回复最多输出多少个 token（约 150 token ≈ 100 英文词）
        - temperature:  随机性参数 0.0-1.0，越高回复越"有创意"但也更容易跑偏
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def chat(
        self,
        system_prompt: str,
        messages: List[dict],
    ) -> LLMResponse:
        """发送请求到云端 API。

        OpenAI 兼容 API 的消息格式：
        [
            {"role": "system", "content": "你是..."},
            {"role": "user", "content": "用户说的话"},
            {"role": "assistant", "content": "AI上一次的回复"},
            {"role": "user", "content": "用户最新说的话"},
        ]
        """
        full_messages = [{"role": "system", "content": system_prompt}]
        full_messages.extend(messages)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        start = time.time()
        response = requests.post(
            self.api_url,
            headers=headers,
            json=body,
            timeout=30,   # 30 秒超时，避免无限等待
        )
        elapsed_ms = (time.time() - start) * 1000

        if response.status_code != 200:
            # API 返回错误时，不崩溃，返回错误信息作为文本
            error_msg = response.text[:200]
            return LLMResponse(
                text=f"[API Error {response.status_code}]: {error_msg}",
                latency_ms=elapsed_ms,
            )

        data = response.json()
        reply_text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return LLMResponse(
            text=reply_text,
            latency_ms=elapsed_ms,
            tokens_used=tokens,
        )

    def is_available(self) -> bool:
        """检查 API 是否可用。发一个空的探测请求。

        注意：这会消耗少量 token。只是确认 key 有效和网络通。
        """
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
                timeout=10,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
