from __future__ import annotations

import pytest

from backend.app.agent.state import (
    apply_reformulated_query,
    attach_query_analysis,
    first_retrieval_request,
    initialize_agent_state,
    record_evidence_grade,
    rewrite_retrieval_request,
)
from backend.app.query_analysis.models import QueryAnalysisResult


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
    insufficient = record_evidence_grade(state, sufficient=False)
    rewritten = apply_reformulated_query(insufficient, "GORE-TEX hardshell washing care")

    assert rewritten["original_query"] == original
    assert rewritten["current_retrieval_query"] == "GORE-TEX hardshell washing care"
    assert rewritten["reformulated_query"] != rewritten["original_query"]
    assert rewrite_retrieval_request(rewritten).__dict__ == {
        "original_query": "GORE-TEX hardshell washing care",
        "bm25_query_text": "GORE-TEX hardshell washing care",
        "brand": "Arc'teryx",
        "technologies": ("GORE-TEX",),
    }


def test_contract_allows_at_most_one_rewrite_and_stops_after_second_insufficiency() -> None:
    state = initialize_agent_state("question")
    first_insufficient = record_evidence_grade(state, sufficient=False)
    rewritten = apply_reformulated_query(first_insufficient, "rewritten question")
    second_insufficient = record_evidence_grade(rewritten, sufficient=False)

    assert second_insufficient["route"] == "insufficient_evidence"
    with pytest.raises(ValueError, match="at most one"):
        apply_reformulated_query(rewritten, "another rewrite")


def test_query_analysis_original_query_must_match_agent_invariant() -> None:
    with pytest.raises(ValueError, match="must match"):
        attach_query_analysis(initialize_agent_state("first"), analysis_for("second"))
