"""Stage 9A orchestration contracts; this module does not execute a graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Required, TypedDict, cast

from backend.app.query_analysis.adapter import to_frozen_retriever_inputs
from backend.app.query_analysis.models import QueryAnalysisResult
from backend.app.retrieval.models import RetrievalCandidate


EvidenceGrade = Literal["unassessed", "sufficient", "insufficient"]
AgentRoute = Literal["retrieve", "rewrite", "ready_for_generation", "insufficient_evidence"]


class AgentState(TypedDict):
    """Minimal durable state contract for the future Stage 9 graph."""

    original_query: Required[str]
    query_analysis: QueryAnalysisResult | None
    bm25_query_text: str | None
    brand: str | None
    technologies: tuple[str, ...]
    current_retrieval_query: str
    retrieval_evidence: tuple[RetrievalCandidate, ...]
    evidence_grade: EvidenceGrade
    rewrite_count: int
    reformulated_query: str | None
    route: AgentRoute


@dataclass(frozen=True)
class FrozenRetrieverRequest:
    """Keyword-equivalent request to the frozen HybridRetriever boundary."""

    original_query: str
    bm25_query_text: str | None
    brand: str | None
    technologies: tuple[str, ...]


def initialize_agent_state(original_query: str) -> AgentState:
    """Start state while retaining the user input exactly as received."""

    if not isinstance(original_query, str) or not original_query.strip():
        raise ValueError("Agent state requires a non-empty original_query.")
    return {
        "original_query": original_query,
        "query_analysis": None,
        "bm25_query_text": None,
        "brand": None,
        "technologies": (),
        "current_retrieval_query": original_query,
        "retrieval_evidence": (),
        "evidence_grade": "unassessed",
        "rewrite_count": 0,
        "reformulated_query": None,
        "route": "retrieve",
    }


def attach_query_analysis(state: AgentState, analysis: QueryAnalysisResult) -> AgentState:
    """Store analysis once and apply only the existing frozen-retriever adapter."""

    if analysis.original_query != state["original_query"]:
        raise ValueError("Query Analysis original_query must match the Agent original_query.")
    adapter = to_frozen_retriever_inputs(analysis)
    updated = dict(state)
    updated.update(
        query_analysis=analysis,
        bm25_query_text=adapter.bm25_query_text,
        brand=adapter.brand,
        technologies=adapter.technologies,
        current_retrieval_query=state["original_query"],
        route="retrieve",
    )
    return cast(AgentState, updated)


def first_retrieval_request(state: AgentState) -> FrozenRetrieverRequest:
    """Build the first frozen-retriever call from retained analysis outputs."""

    if state["query_analysis"] is None:
        raise ValueError("First retrieval requires Query Analysis output.")
    return FrozenRetrieverRequest(
        original_query=state["original_query"],
        bm25_query_text=state["bm25_query_text"],
        brand=state["brand"],
        technologies=state["technologies"],
    )


def record_retrieval_evidence(
    state: AgentState, candidates: tuple[RetrievalCandidate, ...]
) -> AgentState:
    """Persist the current Top-K evidence without judging it."""

    updated = dict(state)
    updated["retrieval_evidence"] = candidates
    return cast(AgentState, updated)


def record_evidence_grade(state: AgentState, *, sufficient: bool) -> AgentState:
    """Apply a future Evidence Judge result to the routing contract."""

    updated = dict(state)
    if sufficient:
        updated.update(evidence_grade="sufficient", route="ready_for_generation")
    elif state["rewrite_count"] == 0:
        updated.update(evidence_grade="insufficient", route="rewrite")
    else:
        updated.update(evidence_grade="insufficient", route="insufficient_evidence")
    return cast(AgentState, updated)


def apply_reformulated_query(state: AgentState, reformulated_query: str) -> AgentState:
    """Record the only permitted rewrite while never replacing original_query."""

    if state["rewrite_count"] != 0:
        raise ValueError("The Stage 9 contract permits at most one Query Rewrite.")
    if not isinstance(reformulated_query, str) or not reformulated_query.strip():
        raise ValueError("Query Rewrite requires a non-empty reformulated_query.")
    updated = dict(state)
    updated.update(
        reformulated_query=reformulated_query,
        current_retrieval_query=reformulated_query,
        rewrite_count=1,
        route="retrieve",
    )
    return cast(AgentState, updated)


def rewrite_retrieval_request(state: AgentState) -> FrozenRetrieverRequest:
    """Build the second call using the rewrite plus first-pass metadata only."""

    reformulated_query = state["reformulated_query"]
    if state["rewrite_count"] != 1 or not reformulated_query:
        raise ValueError("Rewrite retrieval requires exactly one stored reformulated_query.")
    return FrozenRetrieverRequest(
        original_query=reformulated_query,
        bm25_query_text=reformulated_query,
        brand=state["brand"],
        technologies=state["technologies"],
    )
