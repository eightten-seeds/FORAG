"""Qwen-backed Query Analysis with explicit provider and validation errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from backend.app.config import Settings
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


class StructuredOutputClient(Protocol):
    """Small provider seam so QueryAnalyzer tests remain fully offline."""

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_question: str,
        response_format: dict[str, object],
        temperature: float,
        enable_thinking: bool,
    ) -> str: ...


@dataclass(slots=True)
class QwenOpenAICompatibleClient:
    """Minimal wrapper around Model Studio's OpenAI-compatible Chat Completions API."""

    client: Any

    @classmethod
    def from_settings(cls, settings: Settings) -> "QwenOpenAICompatibleClient":
        if settings.llm_provider.lower() != "qwen":
            raise QueryAnalysisConfigurationError(
                "Query Analysis requires LLM_PROVIDER=qwen."
            )
        if not settings.dashscope_api_key.strip():
            raise QueryAnalysisConfigurationError("DASHSCOPE_API_KEY is not configured.")
        if not settings.qwen_base_url.strip():
            raise QueryAnalysisConfigurationError("QWEN_BASE_URL is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject.toml
            raise QueryAnalysisConfigurationError(
                "The OpenAI-compatible client dependency is not installed."
            ) from exc

        return cls(
            OpenAI(
                api_key=settings.dashscope_api_key,
                base_url=settings.qwen_base_url,
                timeout=settings.llm_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        )

    def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_question: str,
        response_format: dict[str, object],
        temperature: float,
        enable_thinking: bool,
    ) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question},
                ],
                response_format=response_format,
                temperature=temperature,
                extra_body={"enable_thinking": enable_thinking},
            )
            content = completion.choices[0].message.content
        except Exception as exc:
            raise QueryAnalysisProviderError("Qwen Query Analysis request failed.") from exc

        if not isinstance(content, str) or not content.strip():
            raise QueryAnalysisProviderError("Qwen Query Analysis response contained no JSON content.")
        return content


@dataclass(slots=True)
class QueryAnalyzer:
    """Analyze one question without changing local ownership of original_query."""

    client: StructuredOutputClient
    model: str
    enable_thinking: bool = False
    temperature: float = 0.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "QueryAnalyzer":
        return cls(
            client=QwenOpenAICompatibleClient.from_settings(settings),
            model=settings.qwen_dev_model,
            enable_thinking=settings.llm_enable_thinking,
        )

    def analyze(self, question: str) -> QueryAnalysisResult:
        if not isinstance(question, str) or not question.strip():
            raise QueryAnalysisValidationError("Query Analysis requires a non-empty user question.")

        try:
            provider_content = self.client.complete(
                model=self.model,
                system_prompt=build_query_analysis_system_prompt(
                    provider_output_json_schema(),
                ),
                user_question=question,
                response_format=provider_response_format(),
                temperature=self.temperature,
                enable_thinking=self.enable_thinking,
            )
        except QueryAnalysisError:
            raise
        except Exception as exc:
            raise QueryAnalysisProviderError("Qwen Query Analysis request failed.") from exc

        try:
            payload = QueryAnalysisPayload.model_validate_json(provider_content)
        except ValidationError as exc:
            raise QueryAnalysisValidationError(
                "Qwen Query Analysis response failed local schema validation."
            ) from exc

        return QueryAnalysisResult(original_query=question, **payload.model_dump())
