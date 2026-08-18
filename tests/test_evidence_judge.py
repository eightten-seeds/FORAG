from __future__ import annotations

import json

import pytest

from backend.app.agent.evidence_judge import (
    EvidenceJudge,
    EvidenceJudgeProviderError,
    EvidenceJudgeValidationError,
)
from backend.app.retrieval.models import RetrievalCandidate


class FakeTransport:
    def __init__(self, content: str | Exception) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def complete_structured(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        if isinstance(self.content, Exception):
            raise self.content
        return self.content


def candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="chunk-1",
        content="Wash the garment following its care label.",
        source_id="source-1",
        source_title="Official care guide",
        source_url="https://example.com/care",
        section_title="Washing",
    )


@pytest.mark.parametrize(
    ("payload", "sufficient", "reason"),
    [
        ({"evidence_sufficient": True, "insufficient_reason": None}, True, None),
        (
            {"evidence_sufficient": False, "insufficient_reason": "retrieval_problem"},
            False,
            "retrieval_problem",
        ),
        (
            {"evidence_sufficient": False, "insufficient_reason": "missing_information"},
            False,
            "missing_information",
        ),
    ],
)
def test_evidence_judge_validates_all_permitted_decisions(
    payload: dict[str, object], sufficient: bool, reason: str | None
) -> None:
    transport = FakeTransport(json.dumps(payload))
    judge = EvidenceJudge(transport, model="qwen3.7-plus")
    question = "Can I machine wash this jacket?"

    decision = judge.judge(question, [candidate()])

    assert decision.evidence_sufficient is sufficient
    assert decision.insufficient_reason == reason
    request = transport.calls[0]
    assert request["model"] == "qwen3.7-plus"
    assert request["enable_thinking"] is False
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["messages"][1]["content"].startswith("Original user question:\n" + question)
    assert "gold" not in request["messages"][1]["content"].lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"evidence_sufficient": False, "insufficient_reason": None},
        {"evidence_sufficient": False, "insufficient_reason": "unknown"},
        {"evidence_sufficient": True, "insufficient_reason": "retrieval_problem"},
    ],
)
def test_evidence_judge_rejects_invalid_or_inconsistent_decisions(payload: dict[str, object]) -> None:
    judge = EvidenceJudge(FakeTransport(json.dumps(payload)), model="qwen3.7-plus")

    with pytest.raises(EvidenceJudgeValidationError, match="schema validation"):
        judge.judge("question", [candidate()])


def test_evidence_judge_normalizes_provider_error() -> None:
    judge = EvidenceJudge(FakeTransport(RuntimeError("network down")), model="qwen3.7-plus")

    with pytest.raises(EvidenceJudgeProviderError, match="request failed"):
        judge.judge("question", [candidate()])
