from __future__ import annotations

import pytest

from backend.app.agent.answer_models import AnswerDraft
from backend.app.agent.citation_validator import (
    AnswerValidationError,
    build_answered_final_response,
    validate_citations,
)
from backend.app.retrieval.models import RetrievalCandidate


def candidate(number: int) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=f"chunk-{number}",
        content=f"evidence {number}",
        source_id=f"source-{number}",
        source_title=f"Official source {number}",
        source_url=f"https://example.com/{number}",
        section_title=f"Section {number}",
    )


def draft(answer: str, ids: list[str]) -> AnswerDraft:
    return AnswerDraft(answer=answer, cited_evidence_ids=ids)


# ---------------------------------------------------------------------------
# 1. inline [E1], structured ["E1"] -> PASS
# ---------------------------------------------------------------------------
def test_valid_single_and_multiple_citations_map_candidate_provenance() -> None:
    evidence = [candidate(1), candidate(2)]
    response = build_answered_final_response(draft("A [E2] then B [E1]", ["E1", "E2"]), evidence)

    assert response.status == "answered"
    assert [source.evidence_id for source in response.sources] == ["E2", "E1"]
    assert response.sources[0].chunk_id == "chunk-2"
    assert response.sources[0].source_title == "Official source 2"
    assert response.sources[0].section_title == "Section 2"
    assert response.sources[0].source_url == "https://example.com/2"


# ---------------------------------------------------------------------------
# 2. inline [E1] [E2], structured ["E1"] -> deterministic reconciliation -> sources E1, E2
# ---------------------------------------------------------------------------
def test_inline_has_more_citations_than_structured_reconciles_to_inline() -> None:
    evidence = [candidate(1), candidate(2)]
    response = build_answered_final_response(draft("See [E1] and [E2]", ["E1"]), evidence)

    assert response.status == "answered"
    assert [source.evidence_id for source in response.sources] == ["E1", "E2"]
    assert response.sources[0].chunk_id == "chunk-1"
    assert response.sources[1].chunk_id == "chunk-2"


# ---------------------------------------------------------------------------
# 3. inline [E2], structured ["E1", "E2"] -> sources only E2
# ---------------------------------------------------------------------------
def test_structured_has_extra_citations_reconciles_to_inline_only() -> None:
    evidence = [candidate(1), candidate(2)]
    response = build_answered_final_response(draft("Only refer to [E2]", ["E1", "E2"]), evidence)

    assert response.status == "answered"
    assert [source.evidence_id for source in response.sources] == ["E2"]
    assert response.sources[0].chunk_id == "chunk-2"


# ---------------------------------------------------------------------------
# 4. duplicate inline [E1] ... [E1] -> source E1 only once in first-appearance order
# ---------------------------------------------------------------------------
def test_duplicate_inline_citation_is_valid_and_sources_are_deduplicated_in_first_order() -> None:
    response = build_answered_final_response(
        draft("First [E1], repeated [E1], then [E2].", ["E1", "E2"]),
        [candidate(1), candidate(2)],
    )

    assert [source.evidence_id for source in response.sources] == ["E1", "E2"]


# ---------------------------------------------------------------------------
# 5. Unknown inline E9 -> FAIL (AnswerValidationError)
# 6. No inline citation -> FAIL (AnswerValidationError)
# 7. Raw URL -> FAIL (AnswerValidationError)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "answer,ids",
    [
        ("Unsupported [E9]", ["E9"]),
        ("Unsupported [E9]", ["E1"]),
        ("Invalid [E0]", ["E0"]),
        ("Guidance [E1] https://example.com/fake", ["E1"]),
        ("Guidance [E1] www.example.com/fake", ["E1"]),
        ("No inline citation", ["E1"]),
    ],
)
def test_invalid_or_unknown_citations_are_rejected(answer: str, ids: list[str]) -> None:
    with pytest.raises(AnswerValidationError):
        validate_citations(draft(answer, ids), [candidate(1), candidate(2)])


# ---------------------------------------------------------------------------
# 8. Provenance still maps directly from current RetrievalCandidate snapshot
# ---------------------------------------------------------------------------
def test_provenance_snapshot_mapping() -> None:
    evidence = [
        RetrievalCandidate(
            chunk_id="c-alpha",
            content="Alpha content",
            source_id="s-alpha",
            source_title="Title Alpha",
            source_url="https://alpha.example.com",
            section_title="Sec Alpha",
        ),
        RetrievalCandidate(
            chunk_id="c-beta",
            content="Beta content",
            source_id="s-beta",
            source_title="Title Beta",
            source_url="https://beta.example.com",
            section_title="Sec Beta",
        ),
    ]
    response = build_answered_final_response(draft("Grounded fact [E2] then [E1]", ["E2"]), evidence)
    assert len(response.sources) == 2
    assert response.sources[0].evidence_id == "E2"
    assert response.sources[0].chunk_id == "c-beta"
    assert response.sources[1].evidence_id == "E1"
    assert response.sources[1].chunk_id == "c-alpha"


# ---------------------------------------------------------------------------
# 9. Graph answer_generation_node does not crash on structured ID divergence
# ---------------------------------------------------------------------------
def test_graph_answer_generation_node_survives_structured_mismatch() -> None:
    from backend.app.agent.evidence_models import EvidenceDecision
    from backend.app.agent.graph import build_agent_graph
    from backend.app.agent.state import initialize_agent_state
    from tests.test_agent_graph import (
        FakeAnalyzer,
        FakeJudge,
        FakeRetriever,
        FakeRewriter,
    )

    class MismatchedAnswerGenerator:
        def generate(self, original_query: str, evidence: tuple[RetrievalCandidate, ...]) -> AnswerDraft:
            # Inline has [E1], but structured cited_evidence_ids has ["E2"]
            return AnswerDraft(answer="Proper guidance [E1]", cited_evidence_ids=["E2"])

    graph = build_agent_graph(
        analyzer=FakeAnalyzer(),
        retriever=FakeRetriever(),
        evidence_judge=FakeJudge([EvidenceDecision(evidence_sufficient=True, insufficient_reason=None)]),
        query_rewriter=FakeRewriter(),
        answer_generator=MismatchedAnswerGenerator(),
    )

    result = graph.invoke(initialize_agent_state("How to care?"))
    assert result["final_response"].status == "answered"
    assert [s.evidence_id for s in result["final_response"].sources] == ["E1"]


def test_final_response_rejects_terminal_status_with_sources() -> None:
    from backend.app.agent.answer_models import FinalResponse, SourceCitation

    with pytest.raises(ValueError, match="must not contain sources"):
        FinalResponse(
            status="needs_more_information",
            answer="Please provide more detail.",
            sources=[
                SourceCitation(
                    evidence_id="E1",
                    chunk_id="chunk-1",
                    source_title="source",
                    section_title="section",
                    source_url="https://example.com",
                )
            ],
        )
