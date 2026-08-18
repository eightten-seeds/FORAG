"""Typed Query Rewrite contract for Stage 9B."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RewriteResult(BaseModel):
    """The sole permitted Query Rewriter output."""

    model_config = ConfigDict(extra="forbid", strict=True)

    reformulated_query: str = Field(min_length=1)

    @field_validator("reformulated_query")
    @classmethod
    def reject_blank_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reformulated_query must not be blank.")
        return normalized


def rewrite_output_json_schema() -> dict[str, object]:
    """Generate provider schema from the local validation model."""

    return RewriteResult.model_json_schema()


def rewrite_response_format() -> dict[str, object]:
    """Build Qwen's strict JSON Schema response-format envelope."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "forag_query_rewrite",
            "strict": True,
            "schema": rewrite_output_json_schema(),
        },
    }
