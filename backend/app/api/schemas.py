"""FastAPI request and response contracts for Stage 11A."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.agent.answer_models import FinalResponse
from backend.app.services.models import ChatTrace, EvidenceItem


class ChatRequest(BaseModel):
    """Public chat input; retrieval and Gold controls remain server-owned."""

    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be blank.")
        return normalized


class ChatResponse(BaseModel):
    """Safe API projection of a Stage 10 FinalResponse and request trace."""

    model_config = ConfigDict(extra="forbid", strict=True)

    final_response: FinalResponse
    evidence: list[EvidenceItem]
    trace: ChatTrace


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    api: str
    runtime: str
    elasticsearch: str
    details: dict[str, str]


class MetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    available: bool
    metrics: None = None
    reason: str
