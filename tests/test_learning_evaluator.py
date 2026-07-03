"""LearningEvaluator 测试。"""

from line_c.engine.learning_evaluator import LearningEvaluator


class TestLearningEvaluator:

    def test_detects_correct_target_word_usage(self):
        evaluator = LearningEvaluator()
        results = evaluator.evaluate("I persist every day.", ["persist"])
        assert len(results) == 1
        assert results[0].attempted is True
        assert results[0].correct is True
        assert results[0].quality == 4

    def test_detects_missing_target_word(self):
        evaluator = LearningEvaluator()
        results = evaluator.evaluate("I practice every day.", ["persist"])
        assert results[0].attempted is False
        assert results[0].correct is False
        assert results[0].quality == 0
        assert results[0].error_type == "missing_target"

    def test_detects_simple_wrong_form(self):
        evaluator = LearningEvaluator()
        results = evaluator.evaluate("I persistence every day.", ["persist"])
        assert results[0].attempted is True
        assert results[0].correct is False
        assert results[0].quality == 2
        assert results[0].error_type == "wrong_form"

    def test_evaluates_multiple_target_words(self):
        evaluator = LearningEvaluator()
        results = evaluator.evaluate("I persist and improve.", ["persist", "summarize"])
        by_word = {r.word: r for r in results}
        assert by_word["persist"].correct is True
        assert by_word["summarize"].attempted is False

    def test_cloud_mode_can_be_enabled_without_breaking_rules(self):
        class DummyLLM:
            def chat(self, system_prompt, messages):
                from line_c.llm.base import LLMResponse
                return LLMResponse(text='{"results": []}')

            def is_available(self):
                return True

        evaluator = LearningEvaluator(llm=DummyLLM(), use_llm=True)
        results = evaluator.evaluate("I persist every day.", ["persist"])
        assert len(results) == 1
        assert results[0].word == "persist"
