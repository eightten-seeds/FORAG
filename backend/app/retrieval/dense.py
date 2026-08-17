from __future__ import annotations

from typing import Protocol

from elasticsearch import Elasticsearch

from backend.app.retrieval.bm25 import RETRIEVAL_SOURCE_FIELDS
from backend.app.retrieval.models import RetrievalCandidate


class QueryEmbedder(Protocol):
    """Minimal E5 dependency needed by the dense retriever."""

    def encode_query(self, query_text: str) -> list[float]: ...


def dense_candidate_from_hit(hit: dict, *, rank: int) -> RetrievalCandidate:
    source = hit["_source"]
    return RetrievalCandidate(
        chunk_id=source["chunk_id"],
        content=source["content"],
        source_id=source["source_id"],
        source_title=source["source_title"],
        source_url=source["source_url"],
        section_title=source["section_title"],
        dense_score=float(hit["_score"]),
        dense_rank=rank,
    )


class DenseRetriever:
    """E5 query embedding plus Elasticsearch kNN over frozen document vectors."""

    def __init__(
        self,
        client: Elasticsearch,
        embedder: QueryEmbedder,
        index_name: str,
        *,
        top_k: int = 20,
        num_candidates: int = 100,
        embedding_dim: int = 384,
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.index_name = index_name
        self.top_k = top_k
        self.num_candidates = num_candidates
        self.embedding_dim = embedding_dim

    def search(self, query_text: str) -> list[RetrievalCandidate]:
        query_vector = self.embedder.encode_query(query_text)
        if len(query_vector) != self.embedding_dim:
            raise ValueError(
                f"query embedding dimension {len(query_vector)} does not match {self.embedding_dim}"
            )
        response = self.client.search(
            index=self.index_name,
            knn={
                "field": "embedding",
                "query_vector": query_vector,
                "k": self.top_k,
                "num_candidates": self.num_candidates,
            },
            size=self.top_k,
            source=list(RETRIEVAL_SOURCE_FIELDS),
        )
        return [
            dense_candidate_from_hit(hit, rank=rank)
            for rank, hit in enumerate(response["hits"]["hits"], start=1)
        ]
