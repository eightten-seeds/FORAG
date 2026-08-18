"""Qwen-backed Query Analysis with explicit provider and validation errors."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.llm.client import QwenOpenAICompatibleClient, StructuredOutputTransport
from backend.app.llm.errors import LLMConfigurationError, LLMProviderError
from backend.app.query_analysis.models import (
    QueryAnalysisPayload,
    QueryAnalysisResult,
    provider_output_json_schema,
    provider_response_format,
)
from backend.app.query_analysis.prompt import build_query_analysis_system_prompt


class QueryAnalysisError(RuntimeError):
    """Base error that future orchestration layers can handle explicitly."""


class QueryAnalysisConfigurationError(QueryAnalysisError):
    """Raised when required Qwen configuration is unavailable."""


class QueryAnalysisProviderError(QueryAnalysisError):
    """Raised when the provider request does not yield usable content."""


class QueryAnalysisValidationError(QueryAnalysisError):
    """Raised when provider output is malformed or violates the typed schema."""


@dataclass(slots=True)
class QueryAnalyzer:
    """Analyze one question without changing local ownership of original_query."""

    client: StructuredOutputTransport
    model: str
    enable_thinking: bool = False
    temperature: float = 0.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "QueryAnalyzer":
        try:
            client = QwenOpenAICompatibleClient.from_settings(settings)
        except LLMConfigurationError as exc:
            raise QueryAnalysisConfigurationError(str(exc)) from exc

        return cls(client=client, model=settings.qwen_dev_model, enable_thinking=settings.llm_enable_thinking)

    def analyze(self, question: str) -> QueryAnalysisResult:
        if not isinstance(question, str) or not question.strip():
            raise QueryAnalysisValidationError("Query Analysis requires a non-empty user question.")

        try:
            provider_content = self.client.complete_structured(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": build_query_analysis_system_prompt(
                            provider_output_json_schema(),
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                response_format=provider_response_format(),
                temperature=self.temperature,
                enable_thinking=self.enable_thinking,
            )
        except LLMProviderError as exc:
            raise QueryAnalysisProviderError(str(exc)) from exc
        except Exception as exc:
            raise QueryAnalysisProviderError("Qwen Query Analysis request failed.") from exc

        try:
            payload = QueryAnalysisPayload.model_validate_json(provider_content)
        except ValidationError as exc:
            raise QueryAnalysisValidationError(
                "Qwen Query Analysis response failed local schema validation."
            ) from exc

        return QueryAnalysisResult(original_query=question, **payload.model_dump())
