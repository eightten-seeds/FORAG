"""Qwen-backed, grounded Evidence Judge business module."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from backend.app.agent.evidence_models import (
    EvidenceDecision,
    evidence_output_json_schema,
    evidence_response_format,
)
from backend.app.agent.evidence_prompt import build_evidence_judge_system_prompt, render_evidence
from backend.app.config import Settings
from backend.app.llm.client import QwenOpenAICompatibleClient, StructuredOutputTransport
from backend.app.llm.errors import LLMConfigurationError, LLMProviderError
from backend.app.retrieval.models import RetrievalCandidate


class EvidenceJudgeError(RuntimeError):
    """Base error for Evidence Judge orchestration handling."""


class EvidenceJudgeConfigurationError(EvidenceJudgeError):
    """Raised when shared Qwen configuration is unavailable."""


class EvidenceJudgeProviderError(EvidenceJudgeError):
    """Raised when the provider request cannot return usable content."""


class EvidenceJudgeValidationError(EvidenceJudgeError):
    """Raised when provider output violates the Evidence Judge contract."""


@dataclass(slots=True)
class EvidenceJudge:
    """Judge current retrieval evidence without performing retrieval or generation."""

    client: StructuredOutputTransport
    model: str
    enable_thinking: bool = False
    temperature: float = 0.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "EvidenceJudge":
        try:
            client = QwenOpenAICompatibleClient.from_settings(settings)
        except LLMConfigurationError as exc:
            raise EvidenceJudgeConfigurationError(str(exc)) from exc
        return cls(client=client, model=settings.qwen_dev_model, enable_thinking=settings.llm_enable_thinking)

    def judge(
        self,
        original_query: str,
        evidence: Sequence[RetrievalCandidate],
    ) -> EvidenceDecision:
        if not isinstance(original_query, str) or not original_query.strip():
            raise EvidenceJudgeValidationError("Evidence Judge requires a non-empty original_query.")
        try:
            content = self.client.complete_structured(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": build_evidence_judge_system_prompt(
                            evidence_output_json_schema(),
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Original user question:\n{original_query}\n\nCurrent Top-K evidence:\n{render_evidence(evidence)}",
                    },
                ],
                response_format=evidence_response_format(),
                temperature=self.temperature,
                enable_thinking=self.enable_thinking,
            )
        except LLMProviderError as exc:
            raise EvidenceJudgeProviderError(str(exc)) from exc
        except Exception as exc:
            raise EvidenceJudgeProviderError("Evidence Judge request failed.") from exc

        try:
            return EvidenceDecision.model_validate_json(content)
        except ValidationError as exc:
            raise EvidenceJudgeValidationError(
                "Evidence Judge response failed local schema validation."
            ) from exc
