"""RAGChecker adapter, schema mapper, and Qwen custom LLM integration."""

from __future__ import annotations

from typing import Any, Callable, Sequence

from ragchecker import RAGChecker, RAGResult, RAGResults
from ragchecker.container import RetrievedDoc

from backend.app.config import Settings
from backend.app.evaluation.models import EvaluationSampleResult
from backend.app.llm.errors import LLMConfigurationError, LLMProviderError


def map_sample_to_ragchecker_result(sample: EvaluationSampleResult) -> RAGResult:
    """Map one evaluation sample to a typed RAGChecker RAGResult.

    Semantics:
    - query_id: stable evaluation ID
    - query: original user question
    - gt_answer: golden reference answer
    - response: FinalResponse.answer (never altered for terminal states)
    - retrieved_context: final Top-K evidence chunks from the frozen pipeline
    """
    retrieved_docs = [
        RetrievedDoc(doc_id=ctx.get("doc_id"), text=ctx.get("text", ""))
        for ctx in sample.retrieved_context
    ]
    return RAGResult(
        query_id=sample.evaluation_id,
        query=sample.question,
        gt_answer=sample.gt_answer,
        response=sample.generated_response,
        retrieved_context=retrieved_docs,
    )


def map_evaluation_to_ragchecker_results(
    samples: Sequence[EvaluationSampleResult],
) -> RAGResults:
    """Map a sequence of evaluation samples into a RAGResults container."""
    results = [map_sample_to_ragchecker_result(sample) for sample in samples]
    return RAGResults(results=results)


class QwenRAGCheckerLLMAdapter:
    """Qwen-backed custom LLM function for RAGChecker claims extraction and checking.

    This adapter adheres strictly to privacy and logging boundaries:
    it does NOT log prompts, evidence texts, candidate answers, API keys,
    Authorization headers, or complete provider payloads.
    """

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        enable_thinking: bool = False,
    ) -> None:
        self.client = client
        self.model = model
        self.enable_thinking = enable_thinking

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        model: str | None = None,
    ) -> "QwenRAGCheckerLLMAdapter":
        if settings.llm_provider.lower() != "qwen":
            raise LLMConfigurationError("RAGChecker LLM adapter requires LLM_PROVIDER=qwen.")
        if not settings.dashscope_api_key.strip():
            raise LLMConfigurationError("DASHSCOPE_API_KEY is not configured.")
        if not settings.qwen_base_url.strip():
            raise LLMConfigurationError("QWEN_BASE_URL is not configured.")

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise LLMConfigurationError("OpenAI client dependency is not installed.") from exc

        client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
        chosen_model = model or settings.ragchecker_extractor_model
        return cls(
            client=client,
            model=chosen_model,
            enable_thinking=settings.llm_enable_thinking,
        )

    def __call__(self, prompts: list[str]) -> list[str]:
        """Execute batch prompt completion for RAGChecker."""
        if not prompts:
            return []

        responses: list[str] = []
        for prompt in prompts:
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    extra_body={"enable_thinking": self.enable_thinking},
                )
                content = completion.choices[0].message.content or ""
                responses.append(content)
            except Exception as exc:
                raise LLMProviderError("RAGChecker Qwen completion request failed.") from exc

        return responses


def run_ragchecker_evaluation(
    rag_results: RAGResults,
    settings: Settings,
    *,
    custom_llm_func: Callable[[list[str]], list[str]] | None = None,
    custom_checker: RAGChecker | None = None,
    save_path: str | None = None,
) -> dict[str, dict[str, float]]:
    """Run RAGChecker evaluation using fixed evaluator models and return metric mappings."""
    if custom_checker is not None:
        checker = custom_checker
    else:
        llm_func = custom_llm_func or QwenRAGCheckerLLMAdapter.from_settings(settings)
        checker = RAGChecker(
            extractor_name=settings.ragchecker_extractor_model,
            checker_name=settings.ragchecker_checker_model,
            custom_llm_api_func=llm_func,
        )

    metrics = checker.evaluate(
        rag_results,
        metrics=["claim_recall", "context_precision", "faithfulness"],
        save_path=save_path,
    )
    return metrics
