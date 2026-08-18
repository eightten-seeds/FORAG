"""Typed RAGService projections with no LangGraph state leakage."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agent.answer_models import FinalResponse
from backend.app.agent.state import EvidenceGrade, InsufficientReason


class EvidenceItem(BaseModel):
    """Minimal final-evidence projection for API consumers."""

    model_config = ConfigDict(extra="forbid", strict=True)

    rank: int = Field(ge=1)
    chunk_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    section_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    content: str = Field(min_length=1)


class RetrievalPassTraceItem(BaseModel):
    """Candidate counts emitted by one real HybridRetriever pass."""

    model_config = ConfigDict(extra="forbid", strict=True)

    pass_index: int = Field(ge=1)
    bm25_count: int = Field(ge=0)
    dense_count: int = Field(ge=0)
    rrf_count: int = Field(ge=0)
    reranked_count: int = Field(ge=0)


class ChatTrace(BaseModel):
    """Safe request-local workflow trace, intentionally smaller than AgentState."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query_analysis_completed: bool
    retrieval_pass_count: int = Field(ge=0)
    rewrite_occurred: bool
    rewrite_count: int = Field(ge=0, le=1)
    evidence_grade: EvidenceGrade
    insufficient_reason: InsufficientReason | None
    final_route: str
    final_status: str
    retrieval_passes: list[RetrievalPassTraceItem]


class RAGServiceResult(BaseModel):
    """Transport-neutral result returned after one compiled graph invocation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    final_response: FinalResponse
    evidence: list[EvidenceItem]
    trace: ChatTrace
