from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from backend.app.retrieval.models import RetrievalCandidate


class CrossEncoderModel(Protocol):
    def predict(
        self,
        sentences: Sequence[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[float]: ...


class CrossEncoderReranker:
    """Reusable Cross-Encoder reranker over canonical evidence content."""

    def __init__(
        self,
        model: CrossEncoderModel,
        *,
        batch_size: int = 8,
        top_k: int = 5,
    ) -> None:
        self.model = model
        self.batch_size = batch_size
        self.top_k = top_k

    @classmethod
    def load(
        cls,
        model_name: str,
        *,
        device: str = "cpu",
        batch_size: int = 8,
        top_k: int = 5,
    ) -> CrossEncoderReranker:
        from sentence_transformers import CrossEncoder

        return cls(CrossEncoder(model_name, device=device), batch_size=batch_size, top_k=top_k)

    def rerank(self, query: str, candidates: Sequence[RetrievalCandidate]) -> list[RetrievalCandidate]:
        if not candidates:
            return []
        pairs = [(query, candidate.content) for candidate in candidates]
        scores = self.model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        scored = [
            candidate.model_copy(update={"rerank_score": float(score)})
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        ordered = sorted(
            enumerate(scored),
            key=lambda item: (-float(item[1].rerank_score), item[0], item[1].chunk_id),
        )[: self.top_k]
        return [candidate.model_copy(update={"rerank_rank": rank}) for rank, (_, candidate) in enumerate(ordered, 1)]
