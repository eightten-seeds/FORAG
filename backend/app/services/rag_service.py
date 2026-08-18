"""Application service for one request-local compiled Agent graph invocation."""

from __future__ import annotations

from typing import Any, Protocol, cast

from backend.app.agent.state import AgentState, initialize_agent_state
from backend.app.observability import time_stage
from backend.app.services.models import (
    ChatTrace,
    EvidenceItem,
    RAGServiceResult,
    RetrievalPassTraceItem,
)


class CompiledAgentGraph(Protocol):
    def invoke(self, input: AgentState) -> dict[str, Any]: ...


class RAGServiceError(RuntimeError):
    """Base service error safe for HTTP-layer mapping."""


class FinalResponseMissingError(RAGServiceError):
    """Raised if a compiled graph violates the Stage 10 final-response contract."""


class RAGService:
    """Invoke the graph once and project only public response fields."""

    def __init__(self, graph: CompiledAgentGraph) -> None:
        self._graph = graph

    def chat(self, question: str) -> RAGServiceResult:
        normalized_question = question.strip() if isinstance(question, str) else ""
        if not normalized_question:
            raise ValueError("question must not be blank.")

        with time_stage("rag_service"):
            result = cast(AgentState, self._graph.invoke(initialize_agent_state(normalized_question)))
        final_response = result.get("final_response")
        if final_response is None:
            raise FinalResponseMissingError("Agent graph completed without final_response.")

        evidence = [
            EvidenceItem(
                rank=rank,
                chunk_id=candidate.chunk_id,
                source_title=candidate.source_title,
                section_title=candidate.section_title,
                source_url=candidate.source_url,
                content=candidate.content,
            )
            for rank, candidate in enumerate(result["retrieval_evidence"], start=1)
        ]
        trace = ChatTrace(
            query_analysis_completed=result["query_analysis"] is not None,
            retrieval_pass_count=result["retrieval_pass_count"],
            rewrite_occurred=result["rewrite_count"] > 0,
            rewrite_count=result["rewrite_count"],
            evidence_grade=result["evidence_grade"],
            insufficient_reason=result["insufficient_reason"],
            final_route=result["route"],
            final_status=final_response.status,
            retrieval_passes=[
                RetrievalPassTraceItem(
                    pass_index=item.pass_index,
                    bm25_count=item.bm25_count,
                    dense_count=item.dense_count,
                    rrf_count=item.rrf_count,
                    reranked_count=item.reranked_count,
                )
                for item in result["retrieval_pass_traces"]
            ],
        )
        return RAGServiceResult(final_response=final_response, evidence=evidence, trace=trace)
