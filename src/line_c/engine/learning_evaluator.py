"""学习评估器。

默认使用可测试的规则评估：
- 用户是否使用了目标词
- 是否出现明显词形错误
- 给出 0-5 quality

CloudLLM 可作为增强评估器：
- 返回 JSON 时采用云端判断
- API 失败或 JSON 不合法时回退规则评估
"""

import json
import re
from typing import Iterable, List, Optional

from ..domain.learning_event import EvaluationResult


class LearningEvaluator:
    """评估用户是否正确尝试了目标词。"""

    def __init__(self, llm=None, use_llm: bool = False):
        self.llm = llm
        self.use_llm = use_llm

    def evaluate(self, user_text: str, target_words: Iterable[str]) -> List[EvaluationResult]:
        """评估一条用户输入中的目标词使用情况。"""
        words = [w.lower().strip() for w in target_words if w and w.strip()]
        if not words:
            return []

        if self.use_llm and self.llm:
            cloud_results = self._evaluate_with_llm(user_text, words)
            if cloud_results:
                return cloud_results

        return self._evaluate_with_rules(user_text, words)

    def _evaluate_with_rules(self, user_text: str, target_words: Iterable[str]) -> List[EvaluationResult]:
        """用本地规则评估，作为默认逻辑和云端失败兜底。"""
        results = []
        normalized = self._normalize(user_text)
        tokens = set(normalized.split())

        for target in target_words:
            if target in tokens:
                results.append(EvaluationResult(
                    word=target,
                    attempted=True,
                    correct=True,
                    quality=4,
                ))
                continue

            wrong_form = self._find_close_form(target, tokens)
            if wrong_form:
                results.append(EvaluationResult(
                    word=target,
                    attempted=True,
                    correct=False,
                    quality=2,
                    error_type="wrong_form",
                    correction=f"Try using '{target}' instead of '{wrong_form}'.",
                    explanation=f"'{wrong_form}' looks like a different form of '{target}'.",
                ))
                continue

            results.append(EvaluationResult(
                word=target,
                attempted=False,
                correct=False,
                quality=0,
                error_type="missing_target",
                correction=f"Try using '{target}' in your next sentence.",
                explanation="The target word did not appear in the learner's sentence.",
            ))

        return results

    def _evaluate_with_llm(self, user_text: str, target_words: List[str]) -> Optional[List[EvaluationResult]]:
        """让云端 LLM 返回结构化评估结果。失败时返回 None。"""
        system_prompt = """You are an English vocabulary learning evaluator.
Return JSON only. No markdown.
Schema:
{
  "results": [
    {
      "word": "target word",
      "attempted": true,
      "correct": true,
      "quality": 0,
      "error_type": "none|missing_target|wrong_form|wrong_meaning|grammar|word_order",
      "correction": "short corrected sentence or suggestion",
      "explanation": "short learner-friendly explanation"
    }
  ]
}
Quality must be an integer 0-5.
Use 0 if the target word was not attempted.
Use 1-2 for wrong usage, 3 for barely acceptable, 4 for correct, 5 for natural and fluent."""
        user_prompt = (
            f"Target words: {', '.join(target_words)}\n"
            f"Learner sentence: {user_text}\n"
            "Evaluate each target word."
        )
        try:
            response = self.llm.chat(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            data = self._parse_json(response.text)
            raw_results = data.get("results", [])
            results = []
            for item in raw_results:
                word = str(item.get("word", "")).lower().strip()
                if word not in target_words:
                    continue
                results.append(EvaluationResult(
                    word=word,
                    attempted=bool(item.get("attempted", False)),
                    correct=bool(item.get("correct", False)),
                    quality=int(item.get("quality", 0)),
                    error_type=item.get("error_type"),
                    correction=item.get("correction"),
                    explanation=item.get("explanation"),
                ))
            return results if len(results) == len(target_words) else None
        except Exception:
            return None

    @staticmethod
    def _parse_json(text: str) -> dict:
        """解析 JSON；兼容模型偶尔包一层说明文字。"""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        if not cleaned.startswith("{"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end >= start:
                cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)

    @staticmethod
    def _normalize(text: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z'\s]", " ", text.lower())
        return " ".join(cleaned.split())

    @staticmethod
    def _find_close_form(target: str, tokens: set[str]) -> str | None:
        """找一个明显像目标词变体的词。

        这是轻量规则，不做复杂 NLP。
        用于捕捉 persistence / persist 这类常见词形问题。
        """
        if len(target) < 5:
            return None

        prefix = target[:5]
        for token in tokens:
            if token != target and len(token) >= 5 and token.startswith(prefix):
                return token
        return None
