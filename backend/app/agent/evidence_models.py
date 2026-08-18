"""Typed Evidence Judge contracts for Stage 9B."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from backend.app.agent.state import InsufficientReason


class EvidenceDecision(BaseModel):
    """A judgment that maps deterministically to the frozen Agent State contract."""

    model_config = ConfigDict(extra="forbid", strict=True)

    evidence_sufficient: bool
    insufficient_reason: InsufficientReason | None

    @model_validator(mode="after")
    def validate_reason_consistency(self) -> "EvidenceDecision":
        if self.evidence_sufficient and self.insufficient_reason is not None:
            raise ValueError("Sufficient evidence must not include an insufficient_reason.")
        if not self.evidence_sufficient and self.insufficient_reason is None:
            raise ValueError("Insufficient evidence requires an insufficient_reason.")
        return self


def evidence_output_json_schema() -> dict[str, object]:
    """Generate provider schema from the local validation model."""

    return EvidenceDecision.model_json_schema()


def evidence_response_format() -> dict[str, object]:
    """Build Qwen's strict JSON Schema response-format envelope."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "forag_evidence_decision",
            "strict": True,
            "schema": evidence_output_json_schema(),
        },
    }
