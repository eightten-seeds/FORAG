from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.models import RetrievalCandidate
from backend.app.retrieval.reranker import CrossEncoderReranker
from backend.app.retrieval.rrf import reciprocal_rank_fusion


@dataclass(frozen=True)
class RetrievalTrace:
    """Candidate lists emitted by each standalone hybrid retrieval stage."""

    bm25_candidates: list[RetrievalCandidate]
    dense_candidates: list[RetrievalCandidate]
    rrf_candidates: list[RetrievalCandidate]
    reranked_candidates: list[RetrievalCandidate]


class HybridRetriever:
    """Production retrieval path: BM25 + Dense -> Python RRF -> Cross-Encoder."""

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        reranker: CrossEncoderReranker,
        *,
        rrf_k: int = 60,
        rrf_top_n: int = 30,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
    ) -> None:
        self.bm25_retriever = bm25_retriever
        self.dense_retriever = dense_retriever
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.rrf_top_n = rrf_top_n
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def retrieve(
        self,
        original_query: str,
        *,
        bm25_query_text: str | None = None,
        brand: str | None = None,
        technologies: Sequence[str] = (),
    ) -> list[RetrievalCandidate]:
        return self.retrieve_with_trace(
            original_query,
            bm25_query_text=bm25_query_text,
            brand=brand,
            technologies=technologies,
        ).reranked_candidates

    def retrieve_with_trace(
        self,
        original_query: str,
        *,
        bm25_query_text: str | None = None,
        brand: str | None = None,
        technologies: Sequence[str] = (),
    ) -> RetrievalTrace:
        """Run the frozen hybrid path while preserving candidate-stage evidence."""
        bm25_candidates = self.bm25_retriever.search(
            bm25_query_text or original_query,
            brand=brand,
            technologies=technologies,
        )
        dense_candidates = self.dense_retriever.search(original_query)
        rrf_candidates = reciprocal_rank_fusion(
            bm25_candidates,
            dense_candidates,
            rrf_k=self.rrf_k,
            top_n=self.rrf_top_n,
            bm25_weight=self.bm25_weight,
            dense_weight=self.dense_weight,
        )
        reranked_candidates = self.reranker.rerank(original_query, rrf_candidates)
        return RetrievalTrace(
            bm25_candidates=bm25_candidates,
            dense_candidates=dense_candidates,
            rrf_candidates=rrf_candidates,
            reranked_candidates=reranked_candidates,
        )
