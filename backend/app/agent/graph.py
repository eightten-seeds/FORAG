"""Stage 9B deterministic LangGraph retrieval control loop."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from langgraph.graph import END, START, StateGraph

from backend.app.agent.answer_models import AnswerDraft
from backend.app.agent.citation_validator import build_answered_final_response
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
from backend.app.agent.terminal_responses import build_terminal_response
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


class GroundedAnswerGenerator(Protocol):
    def generate(
        self,
        original_query: str,
        evidence: Sequence[RetrievalCandidate],
    ) -> AnswerDraft: ...


def build_agent_graph(
    *,
    analyzer: Analyzer,
    retriever: FrozenRetriever,
    evidence_judge: EvidenceJudge,
    query_rewriter: QueryRewriter,
    answer_generator: GroundedAnswerGenerator,
):
    """Build the Stage 10 graph with a frozen one-rewrite retrieval control loop."""

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

    def answer_generation_node(state: AgentState) -> AgentState:
        draft = answer_generator.generate(state["original_query"], state["retrieval_evidence"])
        updated = dict(state)
        updated["final_response"] = build_answered_final_response(draft, state["retrieval_evidence"])
        return updated  # type: ignore[return-value]

    def terminal_response_node(state: AgentState) -> AgentState:
        updated = dict(state)
        updated["final_response"] = build_terminal_response(state)
        return updated  # type: ignore[return-value]

    graph = StateGraph(AgentState)
    graph.add_node("query_analysis", query_analysis_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("evidence_judge", evidence_judge_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("answer_generation", answer_generation_node)
    graph.add_node("terminal_response", terminal_response_node)
    graph.add_edge(START, "query_analysis")
    graph.add_edge("query_analysis", "retrieve")
    graph.add_edge("retrieve", "evidence_judge")
    graph.add_conditional_edges(
        "evidence_judge",
        lambda state: state["route"],
        {
            "ready_for_generation": "answer_generation",
            "insufficient_evidence": "terminal_response",
            "rewrite": "rewrite",
        },
    )
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("answer_generation", END)
    graph.add_edge("terminal_response", END)
    return graph.compile()
