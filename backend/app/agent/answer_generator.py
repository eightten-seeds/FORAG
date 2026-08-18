"""Qwen-backed grounded Answer Generator for Stage 10."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from backend.app.agent.answer_models import AnswerDraft, answer_output_json_schema, answer_response_format
from backend.app.agent.answer_prompt import build_answer_system_prompt, build_answer_user_message
from backend.app.config import Settings
from backend.app.llm.client import QwenOpenAICompatibleClient, StructuredOutputTransport
from backend.app.llm.errors import LLMConfigurationError, LLMProviderError
from backend.app.retrieval.models import RetrievalCandidate


class AnswerGeneratorError(RuntimeError):
    """Base error for Answer Generator orchestration handling."""


class AnswerGeneratorConfigurationError(AnswerGeneratorError):
    """Raised when shared Qwen configuration is unavailable."""


class AnswerGeneratorProviderError(AnswerGeneratorError):
    """Raised when the provider request cannot return usable content."""


class AnswerGeneratorValidationError(AnswerGeneratorError):
    """Raised when provider output violates the Answer Generator contract."""


@dataclass(slots=True)
class AnswerGenerator:
    """Generate a grounded draft only; citation mapping remains deterministic backend work."""

    client: StructuredOutputTransport
    model: str
    enable_thinking: bool = False
    temperature: float = 0.0

    @classmethod
    def from_settings(cls, settings: Settings) -> "AnswerGenerator":
        try:
            client = QwenOpenAICompatibleClient.from_settings(settings)
        except LLMConfigurationError as exc:
            raise AnswerGeneratorConfigurationError(str(exc)) from exc
        return cls(client=client, model=settings.qwen_dev_model, enable_thinking=settings.llm_enable_thinking)

    def generate(
        self,
        original_query: str,
        evidence: Sequence[RetrievalCandidate],
    ) -> AnswerDraft:
        if not isinstance(original_query, str) or not original_query.strip():
            raise AnswerGeneratorValidationError("Answer Generator requires a non-empty original_query.")
        if not evidence:
            raise AnswerGeneratorValidationError("Answer Generator requires non-empty evidence.")
        try:
            content = self.client.complete_structured(
                model=self.model,
                messages=[
                    {"role": "system", "content": build_answer_system_prompt(answer_output_json_schema())},
                    {"role": "user", "content": build_answer_user_message(original_query, evidence)},
                ],
                response_format=answer_response_format(),
                temperature=self.temperature,
                enable_thinking=self.enable_thinking,
            )
        except LLMProviderError as exc:
            raise AnswerGeneratorProviderError(str(exc)) from exc
        except Exception as exc:
            raise AnswerGeneratorProviderError("Answer Generator request failed.") from exc

        try:
            return AnswerDraft.model_validate_json(content)
        except ValidationError as exc:
            raise AnswerGeneratorValidationError(
                "Answer Generator response failed local schema validation."
            ) from exc
