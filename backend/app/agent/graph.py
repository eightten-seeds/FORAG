"""Stage 9B deterministic LangGraph retrieval control loop."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from langgraph.graph import END, START, StateGraph

from backend.app.agent.evidence_judge import EvidenceJudge
from backend.app.agent.query_rewriter import QueryRewriter
from backend.app.agent.state import (
    AgentState,
    apply_reformulated_query,
    attach_query_analysis,
    first_retrieval_request,
    record_evidence_grade,
    record_retrieval_evidence,
    rewrite_retrieval_request,
)
from backend.app.query_analysis.models import QueryAnalysisResult
from backend.app.retrieval.models import RetrievalCandidate


class Analyzer(Protocol):
    def analyze(self, question: str) -> QueryAnalysisResult: ...


class FrozenRetriever(Protocol):
    def retrieve(
        self,
        original_query: str,
        *,
        bm25_query_text: str | None = None,
        brand: str | None = None,
        technologies: Sequence[str] = (),
    ) -> list[RetrievalCandidate]: ...


def build_agent_graph(
    *,
    analyzer: Analyzer,
    retriever: FrozenRetriever,
    evidence_judge: EvidenceJudge,
    query_rewriter: QueryRewriter,
):
    """Build an injectable one-rewrite graph; no generation node is included."""

    def query_analysis_node(state: AgentState) -> AgentState:
        return attach_query_analysis(state, analyzer.analyze(state["original_query"]))

    def retrieve_node(state: AgentState) -> AgentState:
        request = (
            first_retrieval_request(state)
            if state["rewrite_count"] == 0
            else rewrite_retrieval_request(state)
        )
        candidates = retriever.retrieve(
            original_query=request.original_query,
            bm25_query_text=request.bm25_query_text,
            brand=request.brand,
            technologies=request.technologies,
        )
        return record_retrieval_evidence(state, tuple(candidates))

    def evidence_judge_node(state: AgentState) -> AgentState:
        decision = evidence_judge.judge(state["original_query"], state["retrieval_evidence"])
        return record_evidence_grade(
            state,
            sufficient=decision.evidence_sufficient,
            insufficient_reason=decision.insufficient_reason,
        )

    def rewrite_node(state: AgentState) -> AgentState:
        result = query_rewriter.rewrite(state["original_query"], state["retrieval_evidence"])
        return apply_reformulated_query(state, result.reformulated_query)

    graph = StateGraph(AgentState)
    graph.add_node("query_analysis", query_analysis_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("evidence_judge", evidence_judge_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_edge(START, "query_analysis")
    graph.add_edge("query_analysis", "retrieve")
    graph.add_edge("retrieve", "evidence_judge")
    graph.add_conditional_edges(
        "evidence_judge",
        lambda state: state["route"],
        {
            "ready_for_generation": END,
            "insufficient_evidence": END,
            "rewrite": "rewrite",
        },
    )
    graph.add_edge("rewrite", "retrieve")
    return graph.compile()
