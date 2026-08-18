from __future__ import annotations

from collections.abc import Iterable

from backend.app.retrieval.models import RetrievalCandidate


def _minimum_rank(candidate: RetrievalCandidate) -> int:
    return min(rank for rank in (candidate.bm25_rank, candidate.dense_rank) if rank is not None)


def reciprocal_rank_fusion(
    bm25_candidates: Iterable[RetrievalCandidate],
    dense_candidates: Iterable[RetrievalCandidate],
    *,
    rrf_k: int = 60,
    top_n: int = 30,
    bm25_weight: float = 1.0,
    dense_weight: float = 1.0,
) -> list[RetrievalCandidate]:
    """Fuse two ranked lists by rank while preserving their retrieval traces."""
    if rrf_k < 0:
        raise ValueError("rrf_k must be non-negative")
    if top_n < 1:
        raise ValueError("top_n must be at least 1")

    merged: dict[str, RetrievalCandidate] = {}
    scores: dict[str, float] = {}

    for candidates, rank_field, score_field, weight in (
        (bm25_candidates, "bm25_rank", "bm25_score", bm25_weight),
        (dense_candidates, "dense_rank", "dense_score", dense_weight),
    ):
        for candidate in candidates:
            rank = getattr(candidate, rank_field)
            if rank is None:
                raise ValueError(f"{rank_field} is required for RRF")
            if rank < 1:
                raise ValueError(f"{rank_field} must be 1-based")

            if candidate.chunk_id not in merged:
                merged[candidate.chunk_id] = candidate
                scores[candidate.chunk_id] = 0.0
            else:
                existing = merged[candidate.chunk_id]
                merged[candidate.chunk_id] = existing.model_copy(
                    update={rank_field: rank, score_field: getattr(candidate, score_field)}
                )
            scores[candidate.chunk_id] += weight / (rrf_k + rank)

    fused = [
        candidate.model_copy(update={"rrf_score": scores[chunk_id]})
        for chunk_id, candidate in merged.items()
    ]
    return sorted(
        fused,
        key=lambda candidate: (-float(candidate.rrf_score), _minimum_rank(candidate), candidate.chunk_id),
    )[:top_n]
