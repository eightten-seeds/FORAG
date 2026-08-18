"""Stage 9A orchestration contracts; this module does not execute a graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Required, TypedDict, cast

from backend.app.agent.answer_models import FinalResponse
from backend.app.query_analysis.adapter import to_frozen_retriever_inputs
from backend.app.query_analysis.models import QueryAnalysisResult
from backend.app.retrieval.models import RetrievalCandidate


EvidenceGrade = Literal["unassessed", "sufficient", "insufficient"]
InsufficientReason = Literal["retrieval_problem", "missing_information"]
AgentRoute = Literal["retrieve", "rewrite", "ready_for_generation", "insufficient_evidence"]


@dataclass(frozen=True)
class RetrievalPassTrace:
    """Request-local candidate counts from one real HybridRetriever pass."""

    pass_index: int
    bm25_count: int
    dense_count: int
    rrf_count: int
    reranked_count: int


class AgentState(TypedDict):
    """Minimal durable state contract for the future Stage 9 graph."""

    original_query: Required[str]
    query_analysis: QueryAnalysisResult | None
    bm25_query_text: str | None
    brand: str | None
    technologies: tuple[str, ...]
    current_retrieval_query: str
    retrieval_evidence: tuple[RetrievalCandidate, ...]
    retrieval_pass_count: int
    retrieval_pass_traces: tuple[RetrievalPassTrace, ...]
    evidence_grade: EvidenceGrade
    insufficient_reason: InsufficientReason | None
    rewrite_count: int
    reformulated_query: str | None
    route: AgentRoute
    final_response: FinalResponse | None


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
        "retrieval_pass_count": 0,
        "retrieval_pass_traces": (),
        "evidence_grade": "unassessed",
        "insufficient_reason": None,
        "rewrite_count": 0,
        "reformulated_query": None,
        "route": "retrieve",
        "final_response": None,
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
    state: AgentState,
    candidates: tuple[RetrievalCandidate, ...],
    *,
    trace: RetrievalPassTrace | None = None,
) -> AgentState:
    """Persist a retrieval pass and clear any prior evidence assessment."""

    updated = dict(state)
    updated.update(
        retrieval_evidence=candidates,
        retrieval_pass_count=state["retrieval_pass_count"] + 1,
        retrieval_pass_traces=(
            state["retrieval_pass_traces"] + (trace,)
            if trace is not None
            else state["retrieval_pass_traces"]
        ),
        evidence_grade="unassessed",
        insufficient_reason=None,
        route="retrieve",
    )
    return cast(AgentState, updated)


def record_evidence_grade(
    state: AgentState,
    *,
    sufficient: bool,
    insufficient_reason: InsufficientReason | None = None,
) -> AgentState:
    """Apply a future Evidence Judge result to the routing contract."""

    updated = dict(state)
    if sufficient:
        if insufficient_reason is not None:
            raise ValueError("Sufficient evidence must not include an insufficient_reason.")
        updated.update(
            evidence_grade="sufficient",
            insufficient_reason=None,
            route="ready_for_generation",
        )
    elif insufficient_reason not in {"retrieval_problem", "missing_information"}:
        raise ValueError("Insufficient evidence requires a valid insufficient_reason.")
    elif insufficient_reason == "retrieval_problem" and state["rewrite_count"] == 0:
        updated.update(
            evidence_grade="insufficient",
            insufficient_reason=insufficient_reason,
            route="rewrite",
        )
    else:
        updated.update(
            evidence_grade="insufficient",
            insufficient_reason=insufficient_reason,
            route="insufficient_evidence",
        )
    return cast(AgentState, updated)


def apply_reformulated_query(state: AgentState, reformulated_query: str) -> AgentState:
    """Record the only permitted rewrite while never replacing original_query."""

    if state["rewrite_count"] != 0:
        raise ValueError("The Stage 9 contract permits at most one Query Rewrite.")
    if state["route"] != "rewrite" or state["insufficient_reason"] != "retrieval_problem":
        raise ValueError("Query Rewrite requires a first-pass retrieval_problem route.")
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
