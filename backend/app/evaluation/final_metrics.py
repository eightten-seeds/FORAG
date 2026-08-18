"""Serialization contract for the eventual single official Stage 14 result."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping


def build_final_metrics(
    *,
    system_commit: str,
    kb_version: str,
    test_samples: int,
    retrieval_evaluable_samples: int,
    embedding_model: str,
    reranker_model: str,
    pipeline_llm_model: str,
    ragchecker_extractor_model: str,
    ragchecker_checker_model: str,
    success_at_5: float,
    recall_at_5: float,
    ragchecker_metrics: Mapping[str, Mapping[str, float]],
    official_run_id: str,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build a transparent final-metrics artifact from actual evaluator output."""
    retriever_metrics = ragchecker_metrics["retriever_metrics"]
    generator_metrics = ragchecker_metrics["generator_metrics"]
    return {
        "system_commit": system_commit,
        "kb_version": kb_version,
        "test_samples": test_samples,
        "retrieval_evaluable_samples": retrieval_evaluable_samples,
        "embedding_model": embedding_model,
        "reranker_model": reranker_model,
        "pipeline_llm_model": pipeline_llm_model,
        "ragchecker_extractor_model": ragchecker_extractor_model,
        "ragchecker_checker_model": ragchecker_checker_model,
        "success_at_5": success_at_5,
        "recall_at_5": recall_at_5,
        "claim_recall": retriever_metrics["claim_recall"],
        "context_precision": retriever_metrics["context_precision"],
        "faithfulness": generator_metrics["faithfulness"],
        "official_run_id": official_run_id,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
