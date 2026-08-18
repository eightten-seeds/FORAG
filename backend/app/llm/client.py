"""Shared Qwen/OpenAI-compatible structured-output transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from backend.app.config import Settings
from backend.app.llm.errors import LLMConfigurationError, LLMProviderError


class StructuredOutputTransport(Protocol):
    """Transport seam for consumers that own their own prompt and schema."""

    def complete_structured(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, object],
        temperature: float,
        enable_thinking: bool,
    ) -> str: ...


@dataclass(slots=True)
class QwenOpenAICompatibleClient:
    """Model Studio transport with no consumer-specific prompt or schema knowledge."""

    client: Any

    @classmethod
    def from_settings(cls, settings: Settings) -> "QwenOpenAICompatibleClient":
        if settings.llm_provider.lower() != "qwen":
            raise LLMConfigurationError("Shared LLM transport requires LLM_PROVIDER=qwen.")
        if not settings.dashscope_api_key.strip():
            raise LLMConfigurationError("DASHSCOPE_API_KEY is not configured.")
        if not settings.qwen_base_url.strip():
            raise LLMConfigurationError("QWEN_BASE_URL is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject.toml
            raise LLMConfigurationError(
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

    def complete_structured(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, object],
        temperature: float,
        enable_thinking: bool,
    ) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format=response_format,
                temperature=temperature,
                extra_body={"enable_thinking": enable_thinking},
            )
            content = completion.choices[0].message.content
        except Exception as exc:
            raise LLMProviderError("Qwen OpenAI-compatible request failed.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Qwen response contained no structured-output content.")
        return content
