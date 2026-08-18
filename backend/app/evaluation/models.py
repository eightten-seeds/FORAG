"""Data models and serialization contracts for Stage 14 Final Evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationSampleResult:
    """Per-sample result from the Final Evaluation Pipeline."""

    evaluation_id: str
    line_number: int
    question: str
    split: str
    category: str
    gold_chunk_ids: list[str]
    gt_answer: str
    final_response_status: str
    generated_response: str
    final_top5_chunk_ids: list[str]
    retrieved_context: list[dict[str, str]]
    rewrite_count: int
    retrieval_pass_count: int
    success_at_5: bool
    recall_at_5: float
    is_retrieval_evaluable: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinalPipelineExecutionResult:
    """Aggregated outcome of evaluating a dataset against the final pipeline."""

    split: str
    system_commit: str
    kb_version: str
    pipeline_llm_model: str
    embedding_model: str
    reranker_model: str
    total_samples: int
    retrieval_evaluable_samples: int
    excluded_non_retrieval_samples: int
    successes_at_5: int
    misses_at_5: int
    success_at_5: float
    recall_at_5: float
    samples: list[EvaluationSampleResult]

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": 14,
            "split": self.split,
            "system_commit": self.system_commit,
            "kb_version": self.kb_version,
            "pipeline_llm_model": self.pipeline_llm_model,
            "embedding_model": self.embedding_model,
            "reranker_model": self.reranker_model,
            "total_samples": self.total_samples,
            "retrieval_evaluable_samples": self.retrieval_evaluable_samples,
            "excluded_non_retrieval_samples": self.excluded_non_retrieval_samples,
            "successes_at_5": self.successes_at_5,
            "misses_at_5": self.misses_at_5,
            "success_at_5": self.success_at_5,
            "recall_at_5": self.recall_at_5,
            "samples": [sample.as_dict() for sample in self.samples],
        }
