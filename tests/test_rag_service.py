from __future__ import annotations

import pytest

from backend.app.agent.answer_models import FinalResponse, SourceCitation
from backend.app.agent.state import initialize_agent_state
from backend.app.retrieval.models import RetrievalCandidate
from backend.app.services.rag_service import FinalResponseMissingError, RAGService


def candidate(chunk_id: str = "chunk-1") -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        content="Evidence content",
        source_id="source-1",
        source_title="Official guide",
        source_url="https://example.com/care",
        section_title="Care",
    )


class FakeGraph:
    def __init__(self, *, final_response: FinalResponse | None) -> None:
        self.final_response = final_response
        self.inputs: list[dict[str, object]] = []

    def invoke(self, input: dict[str, object]) -> dict[str, object]:
        self.inputs.append(input)
        result = dict(input)
        result.update(
            query_analysis=object(),
            retrieval_evidence=(candidate(),),
            retrieval_pass_count=2,
            rewrite_count=1,
            evidence_grade="sufficient",
            insufficient_reason=None,
            route="ready_for_generation",
            final_response=self.final_response,
        )
        return result


def answered_response() -> FinalResponse:
    return FinalResponse(
        status="answered",
        answer="Grounded answer [E1]",
        sources=[
            SourceCitation(
                evidence_id="E1",
                chunk_id="chunk-1",
                source_title="Official guide",
                section_title="Care",
                source_url="https://example.com/care",
            )
        ],
    )


def test_rag_service_normalizes_question_preserves_original_query_and_projects_safe_result() -> None:
    graph = FakeGraph(final_response=answered_response())
    result = RAGService(graph).chat("  question  ")

    assert graph.inputs[0]["original_query"] == "question"
    assert result.final_response.status == "answered"
    assert result.evidence[0].chunk_id == "chunk-1"
    assert result.trace.retrieval_pass_count == 2
    assert result.trace.rewrite_occurred is True
    assert result.trace.retrieval_passes == []


def test_rag_service_rejects_blank_question_before_graph_invocation() -> None:
    graph = FakeGraph(final_response=answered_response())
    with pytest.raises(ValueError, match="blank"):
        RAGService(graph).chat("   ")
    assert graph.inputs == []


def test_rag_service_requires_final_response() -> None:
    with pytest.raises(FinalResponseMissingError, match="final_response"):
        RAGService(FakeGraph(final_response=None)).chat("question")
