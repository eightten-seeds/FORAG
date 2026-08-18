from pydantic import BaseModel, ConfigDict, Field


class RetrievalCandidate(BaseModel):
    """One retrieved KB chunk, with optional per-retriever ranking details."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    section_title: str = Field(min_length=1)

    bm25_score: float | None = None
    bm25_rank: int | None = Field(default=None, ge=1)
    dense_score: float | None = None
    dense_rank: int | None = Field(default=None, ge=1)
    rrf_score: float | None = None
    rerank_score: float | None = None
    rerank_rank: int | None = Field(default=None, ge=1)
