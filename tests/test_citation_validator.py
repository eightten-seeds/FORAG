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


def test_valid_single_and_multiple_citations_map_candidate_provenance() -> None:
    evidence = [candidate(1), candidate(2)]
    response = build_answered_final_response(draft("A [E2] then B [E1]", ["E1", "E2"]), evidence)

    assert response.status == "answered"
    assert [source.evidence_id for source in response.sources] == ["E2", "E1"]
    assert response.sources[0].chunk_id == "chunk-2"
    assert response.sources[0].source_title == "Official source 2"
    assert response.sources[0].section_title == "Section 2"
    assert response.sources[0].source_url == "https://example.com/2"


@pytest.mark.parametrize(
    "answer,ids",
    [
        ("Unsupported [E9]", ["E9"]),
        ("Invalid [E0]", ["E0"]),
        ("Guidance [E1] https://example.com/fake", ["E1"]),
        ("Guidance [E1] www.example.com/fake", ["E1"]),
        ("No inline citation", ["E1"]),
        ("Mismatch [E1]", ["E2"]),
    ],
)
def test_invalid_or_inconsistent_citations_are_rejected(answer: str, ids: list[str]) -> None:
    with pytest.raises(AnswerValidationError):
        validate_citations(draft(answer, ids), [candidate(1), candidate(2)])


def test_duplicate_inline_citation_is_valid_and_sources_are_deduplicated_in_first_order() -> None:
    response = build_answered_final_response(
        draft("First [E1], repeated [E1], then [E2].", ["E1", "E2"]),
        [candidate(1), candidate(2)],
    )

    assert [source.evidence_id for source in response.sources] == ["E1", "E2"]


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
