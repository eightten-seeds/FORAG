"""Typed Answer Generation and final user-response contracts for Stage 10."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


FinalResponseStatus = Literal[
    "answered",
    "needs_more_information",
    "insufficient_evidence",
]


class SourceCitation(BaseModel):
    """A deterministic provenance projection from one retrieval candidate."""

    model_config = ConfigDict(extra="forbid", strict=True)

    evidence_id: str = Field(pattern=r"^E[1-9]\d*$")
    chunk_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    section_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)


class FinalResponse(BaseModel):
    """The single typed terminal response stored by the Agent graph."""

    model_config = ConfigDict(extra="forbid", strict=True)

    status: FinalResponseStatus
    answer: str = Field(min_length=1)
    sources: list[SourceCitation]

    @field_validator("answer")
    @classmethod
    def reject_blank_answer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("answer must not be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_status_source_consistency(self) -> "FinalResponse":
        if self.status == "answered" and not self.sources:
            raise ValueError("answered FinalResponse requires at least one source.")
        if self.status != "answered" and self.sources:
            raise ValueError("terminal non-answer FinalResponse must not contain sources.")
        return self


class AnswerDraft(BaseModel):
    """The strict structured output that the Answer Generator may produce."""

    model_config = ConfigDict(extra="forbid", strict=True)

    answer: str = Field(min_length=1)
    cited_evidence_ids: list[str] = Field(min_length=1)

    @field_validator("answer")
    @classmethod
    def reject_blank_answer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("answer must not be blank.")
        return normalized

    @field_validator("cited_evidence_ids")
    @classmethod
    def normalize_citation_ids(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("cited_evidence_ids must not contain blank values.")
        return normalized


def answer_output_json_schema() -> dict[str, object]:
    """Generate the provider schema from the local validation model."""

    return AnswerDraft.model_json_schema()


def answer_response_format() -> dict[str, object]:
    """Build Qwen's strict JSON Schema response-format envelope."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "forag_grounded_answer",
            "strict": True,
            "schema": answer_output_json_schema(),
        },
    }
