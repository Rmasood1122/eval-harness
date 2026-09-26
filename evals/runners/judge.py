"""Judge adapter: real LLM judge when available, MockJudge otherwise.

MockJudge is a lexical-overlap proxy so the harness runs end-to-end with zero API
keys. It is DEMO-ONLY: on a real project, install deepeval + set an API key, and
validate the judge against 30-50 hand labels before trusting a single score.
"""
from __future__ import annotations

import os
import re

_WORD = re.compile(r"[a-z0-9]+")


def _words(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


_STOP = _words("the a an is are and or of for to in on with also that this it its within note")


class MockJudge:
    """Deterministic lexical proxy for faithfulness / relevancy. Demo only."""

    name = "mock-lexical-judge"

    def faithfulness(self, answer: str, context_texts: list[str]) -> float:
        """Fraction of answer sentences whose content words are supported by context."""
        ctx = _words(" ".join(context_texts)) - _STOP
        sentences = [s for s in re.split(r"[.!?]+", answer) if _words(s) - _STOP]
        if not sentences:
            return 1.0
        supported = 0
        for s in sentences:
            sw = _words(s) - _STOP
            if not sw or len(sw & ctx) / len(sw) >= 0.7:
                supported += 1
        return supported / len(sentences)

    def relevancy(self, answer: str, question: str) -> float:
        qw = _words(question) - _STOP
        aw = _words(answer) - _STOP
        if not qw:
            return 1.0
        return min(1.0, len(qw & aw) / max(1, len(qw)) + 0.4)


def get_judge():
    """Prefer a real judge (DeepEval + API key); fall back to MockJudge."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        try:
            from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric  # noqa: F401
            from deepeval.test_case import LLMTestCase

            class DeepEvalJudge:
                name = "deepeval-geval"

                def faithfulness(self, answer, context_texts):
                    m = FaithfulnessMetric(threshold=0.0)
                    m.measure(LLMTestCase(input="", actual_output=answer,
                                          retrieval_context=context_texts))
                    return float(m.score)

                def relevancy(self, answer, question):
                    m = AnswerRelevancyMetric(threshold=0.0)
                    m.measure(LLMTestCase(input=question, actual_output=answer))
                    return float(m.score)

            return DeepEvalJudge()
        except ImportError:
            pass
    return MockJudge()
