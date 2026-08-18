"""Qwen-backed retrieval-only Query Rewriter business module."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from backend.app.agent.rewrite_models import (
    RewriteResult,
    rewrite_output_json_schema,
    rewrite_response_format,
)
from backend.app.agent.rewrite_prompt import (
    build_query_rewrite_system_prompt,
    build_query_rewrite_user_message,
)
from backend.app.config import Settings
from backend.app.llm.client import QwenOpenAICompatibleClient, StructuredOutputTransport
from backend.app.llm.errors import LLMConfigurationError, LLMProviderError
from backend.app.retrieval.models import RetrievalCandidate


class QueryRewriteError(RuntimeError):
    """Base error for Query Rewrite orchestration handling."""


class QueryRewriteConfigurationError(QueryRewriteError):
    """Raised when shared Qwen configuration is unavailable."""


class QueryRewriteProviderError(QueryRewriteError):
    """Raised when the provider request cannot return usable content."""


class QueryRewriteValidationError(QueryRewriteError):
    """Raised when provider output violates the Query Rewrite contract."""


@dataclass(slots=True)
class QueryRewriter:
    """Create one reformulated retrieval query without changing original_query."""

    client: StructuredOutputTransport
    model: str
    enable_thinking: bool = False
    temperature: float = 0.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "QueryRewriter":
        try:
            client = QwenOpenAICompatibleClient.from_settings(settings)
        except LLMConfigurationError as exc:
            raise QueryRewriteConfigurationError(str(exc)) from exc
        return cls(client=client, model=settings.qwen_dev_model, enable_thinking=settings.llm_enable_thinking)

    def rewrite(
        self,
        original_query: str,
        evidence: Sequence[RetrievalCandidate],
    ) -> RewriteResult:
        if not isinstance(original_query, str) or not original_query.strip():
            raise QueryRewriteValidationError("Query Rewrite requires a non-empty original_query.")
        try:
            content = self.client.complete_structured(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": build_query_rewrite_system_prompt(
                            rewrite_output_json_schema(),
                        ),
                    },
                    {
                        "role": "user",
                        "content": build_query_rewrite_user_message(original_query, evidence),
                    },
                ],
                response_format=rewrite_response_format(),
                temperature=self.temperature,
                enable_thinking=self.enable_thinking,
            )
        except LLMProviderError as exc:
            raise QueryRewriteProviderError(str(exc)) from exc
        except Exception as exc:
            raise QueryRewriteProviderError("Query Rewrite request failed.") from exc

        try:
            return RewriteResult.model_validate_json(content)
        except ValidationError as exc:
            raise QueryRewriteValidationError(
                "Query Rewrite response failed local schema validation."
            ) from exc
