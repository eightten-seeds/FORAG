"""Typed contracts for the Stage 8A Query Analysis boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StructuredQuery(BaseModel):
    """Structured entities extracted from the user question only."""

    model_config = ConfigDict(extra="forbid", strict=True)

    brand: str | None
    garment_type: str | None
    technology: list[str]
    issue_type: str | None
    intent: str | None
    # ARCHITECTURE.md defines this optional state field; it is never adapted to Retriever input.
    care_stage: str | None = None

    @field_validator("brand", "garment_type", "issue_type", "intent", "care_stage")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("technology")
    @classmethod
    def normalize_technologies(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class QueryAnalysisPayload(BaseModel):
    """The complete provider response, before local ownership is attached."""

    model_config = ConfigDict(extra="forbid", strict=True)

    structured_query: StructuredQuery
    lexical_terms_en: list[str]


class QueryAnalysisResult(QueryAnalysisPayload):
    """Validated Query Analysis output with the locally owned original question."""

    original_query: str = Field(min_length=1)


def provider_output_json_schema() -> dict[str, object]:
    """Generate the provider schema from the same typed payload model we validate."""

    return QueryAnalysisPayload.model_json_schema()


def provider_response_format() -> dict[str, object]:
    """Build Qwen's strict JSON Schema response-format envelope."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "forag_query_analysis",
            "strict": True,
            "schema": provider_output_json_schema(),
        },
    }
