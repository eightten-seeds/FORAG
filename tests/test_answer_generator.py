from __future__ import annotations

import json

import pytest

from backend.app.agent.answer_generator import (
    AnswerGenerator,
    AnswerGeneratorProviderError,
    AnswerGeneratorValidationError,
)
from backend.app.retrieval.models import RetrievalCandidate


class FakeTransport:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def complete_structured(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="chunk-1",
        content="Restore water repellency only as the supplied care guide directs.",
        source_id="source-1",
        source_title="Official Care Guide",
        source_url="https://example.com/care",
        section_title="Water repellency",
    )


def test_answer_generator_uses_strict_schema_and_preserves_original_question() -> None:
    transport = FakeTransport(
        json.dumps({"answer": "请按护理指南处理。[E1]", "cited_evidence_ids": ["E1"]})
    )
    generator = AnswerGenerator(transport, model="qwen3.7-plus")

    result = generator.generate("我的外套不挂水珠了怎么办？", [candidate()])

    assert result.cited_evidence_ids == ["E1"]
    request = transport.calls[0]
    assert request["model"] == "qwen3.7-plus"
    assert request["enable_thinking"] is False
    response_format = request["response_format"]
    assert response_format["type"] == "json_schema"  # type: ignore[index]
    assert response_format["json_schema"]["strict"] is True  # type: ignore[index]
    user_message = request["messages"][1]["content"]  # type: ignore[index]
    assert "我的外套不挂水珠了怎么办？" in user_message
    assert "https://example.com/care" not in user_message


@pytest.mark.parametrize(
    "payload",
    [
        {"answer": "", "cited_evidence_ids": ["E1"]},
        {"answer": "no citation list", "cited_evidence_ids": []},
    ],
)
def test_answer_generator_rejects_invalid_local_output(payload: dict[str, object]) -> None:
    generator = AnswerGenerator(FakeTransport(json.dumps(payload)), model="qwen3.7-plus")

    with pytest.raises(AnswerGeneratorValidationError, match="schema validation"):
        generator.generate("question", [candidate()])


def test_answer_generator_rejects_empty_evidence_without_provider_call() -> None:
    transport = FakeTransport("{}")
    generator = AnswerGenerator(transport, model="qwen3.7-plus")

    with pytest.raises(AnswerGeneratorValidationError, match="non-empty evidence"):
        generator.generate("question", [])
    assert transport.calls == []


def test_answer_generator_normalizes_provider_error() -> None:
    generator = AnswerGenerator(FakeTransport(RuntimeError("network down")), model="qwen3.7-plus")

    with pytest.raises(AnswerGeneratorProviderError, match="request failed"):
        generator.generate("question", [candidate()])
