"""Deterministic Stage 8A adapter to the frozen HybridRetriever interface."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.query_analysis.models import QueryAnalysisResult


class FrozenRetrieverInputs(BaseModel):
    """Exactly the keyword arguments accepted by the frozen Retriever boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bm25_query_text: str | None
    brand: str | None
    technologies: tuple[str, ...]


def to_frozen_retriever_inputs(result: QueryAnalysisResult) -> FrozenRetrieverInputs:
    """Map only the documented Stage 8A fields to frozen Retriever inputs."""

    terms = [
        term.strip()
        for term in result.lexical_terms_en
        if isinstance(term, str) and term.strip()
    ]
    bm25_query_text = " ".join(terms) if terms else None

    return FrozenRetrieverInputs(
        bm25_query_text=bm25_query_text,
        brand=result.structured_query.brand,
        technologies=tuple(result.structured_query.technology),
    )
