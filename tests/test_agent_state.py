from __future__ import annotations

import pytest

from backend.app.agent.state import (
    apply_reformulated_query,
    attach_query_analysis,
    first_retrieval_request,
    initialize_agent_state,
    record_evidence_grade,
    record_retrieval_evidence,
    rewrite_retrieval_request,
)
from backend.app.query_analysis.models import QueryAnalysisResult
from backend.app.retrieval.models import RetrievalCandidate


def analysis_for(question: str) -> QueryAnalysisResult:
    return QueryAnalysisResult.model_validate(
        {
            "original_query": question,
            "lexical_terms_en": [" GORE-TEX ", "", "DWR"],
            "structured_query": {
                "brand": "Arc'teryx",
                "garment_type": "hardshell",
                "technology": ["GORE-TEX"],
                "issue_type": "water_repellency_loss",
                "intent": "care_troubleshooting",
                "care_stage": "restore_dwr",
            },
        }
    )


def test_first_retrieval_uses_adapter_and_never_unsupported_structured_fields() -> None:
    question = "我的 GORE-TEX 冲锋衣不挂水珠了怎么办？"
    state = attach_query_analysis(initialize_agent_state(question), analysis_for(question))

    assert first_retrieval_request(state).__dict__ == {
        "original_query": question,
        "bm25_query_text": "GORE-TEX DWR",
        "brand": "Arc'teryx",
        "technologies": ("GORE-TEX",),
    }
    assert state["query_analysis"].structured_query.garment_type == "hardshell"
    assert set(first_retrieval_request(state).__dict__) == {
        "original_query",
        "bm25_query_text",
        "brand",
        "technologies",
    }


def test_rewrite_keeps_original_query_and_reuses_first_pass_metadata() -> None:
    original = "我的衣服怎么洗？"
    state = attach_query_analysis(initialize_agent_state(original), analysis_for(original))
    insufficient = record_evidence_grade(
        state,
        sufficient=False,
        insufficient_reason="retrieval_problem",
    )
    rewritten = apply_reformulated_query(insufficient, "GORE-TEX hardshell washing care")

    assert rewritten["original_query"] == original
    assert rewritten["current_retrieval_query"] == "GORE-TEX hardshell washing care"
    assert rewritten["reformulated_query"] != rewritten["original_query"]
    assert rewritten["query_analysis"] is state["query_analysis"]
    assert rewrite_retrieval_request(rewritten).__dict__ == {
        "original_query": "GORE-TEX hardshell washing care",
        "bm25_query_text": "GORE-TEX hardshell washing care",
        "brand": "Arc'teryx",
        "technologies": ("GORE-TEX",),
    }


def test_sufficient_evidence_routes_to_generation_without_insufficient_reason() -> None:
    state = record_evidence_grade(initialize_agent_state("question"), sufficient=True)

    assert state["evidence_grade"] == "sufficient"
    assert state["insufficient_reason"] is None
    assert state["route"] == "ready_for_generation"


def test_first_retrieval_problem_routes_to_one_rewrite() -> None:
    state = record_evidence_grade(
        initialize_agent_state("question"),
        sufficient=False,
        insufficient_reason="retrieval_problem",
    )

    assert state["evidence_grade"] == "insufficient"
    assert state["insufficient_reason"] == "retrieval_problem"
    assert state["route"] == "rewrite"


def test_missing_information_never_routes_to_rewrite() -> None:
    state = record_evidence_grade(
        initialize_agent_state("question"),
        sufficient=False,
        insufficient_reason="missing_information",
    )

    assert state["route"] == "insufficient_evidence"
    with pytest.raises(ValueError, match="retrieval_problem"):
        apply_reformulated_query(state, "must not rewrite")


def test_retrieval_problem_after_one_rewrite_stops_and_preserves_max_one_invariant() -> None:
    state = initialize_agent_state("question")
    first_insufficient = record_evidence_grade(
        state,
        sufficient=False,
        insufficient_reason="retrieval_problem",
    )
    rewritten = apply_reformulated_query(first_insufficient, "rewritten question")
    second_insufficient = record_evidence_grade(
        rewritten,
        sufficient=False,
        insufficient_reason="retrieval_problem",
    )

    assert second_insufficient["route"] == "insufficient_evidence"
    with pytest.raises(ValueError, match="at most one"):
        apply_reformulated_query(rewritten, "another rewrite")


def test_missing_information_after_one_rewrite_stops() -> None:
    first_insufficient = record_evidence_grade(
        initialize_agent_state("question"),
        sufficient=False,
        insufficient_reason="retrieval_problem",
    )
    rewritten = apply_reformulated_query(first_insufficient, "rewritten question")

    state = record_evidence_grade(
        rewritten,
        sufficient=False,
        insufficient_reason="missing_information",
    )

    assert state["route"] == "insufficient_evidence"


@pytest.mark.parametrize("reason", [None, "unknown"])
def test_invalid_or_missing_insufficient_reason_is_rejected(reason: object) -> None:
    with pytest.raises(ValueError, match="valid insufficient_reason"):
        record_evidence_grade(
            initialize_agent_state("question"),
            sufficient=False,
            insufficient_reason=reason,  # type: ignore[arg-type]
        )


def test_query_analysis_original_query_must_match_agent_invariant() -> None:
    with pytest.raises(ValueError, match="must match"):
        attach_query_analysis(initialize_agent_state("first"), analysis_for("second"))


def test_new_retrieval_evidence_resets_stale_evidence_assessment() -> None:
    first_insufficient = record_evidence_grade(
        initialize_agent_state("question"),
        sufficient=False,
        insufficient_reason="retrieval_problem",
    )
    rewritten = apply_reformulated_query(first_insufficient, "rewritten question")
    candidate = RetrievalCandidate(
        chunk_id="chunk-1",
        content="new evidence",
        source_id="source-1",
        source_title="title",
        source_url="https://example.com",
        section_title="section",
    )

    refreshed = record_retrieval_evidence(rewritten, (candidate,))

    assert refreshed["evidence_grade"] == "unassessed"
    assert refreshed["insufficient_reason"] is None
    assert refreshed["route"] == "retrieve"
