"""CloudLLM 结构化评估测试。"""

from line_c.domain.learning_event import EvaluationResult
from line_c.engine.learning_evaluator import LearningEvaluator
from line_c.llm.base import LLMResponse


class DummyCloudLLM:
    def __init__(self, text):
        self.text = text

    def chat(self, system_prompt, messages):
        return LLMResponse(text=self.text)

    def is_available(self):
        return True


class TestCloudEvaluation:

    def test_parses_cloud_json_results(self):
        llm = DummyCloudLLM(
            '{"results":[{"word":"persist","attempted":true,"correct":true,"quality":5,"error_type":"none","correction":"Good.","explanation":"Natural usage."}]}'
        )
        evaluator = LearningEvaluator(llm=llm, use_llm=True)
        results = evaluator.evaluate("I persist every day.", ["persist"])
        assert len(results) == 1
        assert results[0].correct is True
        assert results[0].quality == 5

    def test_falls_back_to_rules_when_json_invalid(self):
        llm = DummyCloudLLM("not json at all")
        evaluator = LearningEvaluator(llm=llm, use_llm=True)
        results = evaluator.evaluate("I persist every day.", ["persist"])
        assert len(results) == 1
        assert results[0].correct is True
        assert results[0].quality == 4
