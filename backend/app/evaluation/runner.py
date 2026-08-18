"""Stage 14 Final Pipeline Evaluation Runner with strict leakage and terminal state contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

from ragchecker import RAGResults

from backend.app.agent.state import initialize_agent_state
from backend.app.config import Settings
from backend.app.evaluation.final_pipeline import FinalEvaluationPipeline
from backend.app.evaluation.models import EvaluationSampleResult, FinalPipelineExecutionResult
from backend.app.evaluation.ragchecker_adapter import map_evaluation_to_ragchecker_results
from backend.app.retrieval.evaluation import NON_RETRIEVAL_CATEGORIES, VALID_SPLITS


def get_system_commit(cwd: Path | None = None) -> str:
    """Retrieve the current Git commit hash."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd or Path.cwd(),
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def evaluate_final_test(
    records: Sequence[dict],
    *,
    pipeline: FinalEvaluationPipeline,
    settings: Settings,
    split: str = "test",
    system_commit: str | None = None,
) -> tuple[FinalPipelineExecutionResult, RAGResults]:
    """Execute evaluation over the final frozen pipeline with leakage boundaries.

    Strict Contracts:
    1. Only `question` enters the Agent Pipeline (Query Analysis -> Hybrid Retrieval -> Judge -> ...).
    2. `gold_chunk_ids`, `gt_answer`, and `category` are unavailable to all pipeline components
       and are read strictly after `FinalResponse` and final evidence are fixed.
    3. Final Evidence Top-5 (second pass if rewritten, first pass otherwise) is scored for Recall@5.
    4. Terminal responses (`needs_more_information`, `insufficient_evidence`) are retained
       and mapped to RAGChecker without alteration or dropping.
    5. Non-retrieval categories are excluded from Recall@5 calculation according to contract.
    """
    if split not in VALID_SPLITS:
        raise ValueError(f"split must be one of {sorted(VALID_SPLITS)}")

    filtered_records = [r for r in records if r.get("split") == split]
    if not filtered_records:
        raise ValueError(f"No records found for split='{split}'.")

    kb_versions = {r.get("kb_version") for r in filtered_records if r.get("kb_version")}
    kb_version = kb_versions.pop() if len(kb_versions) == 1 else "kb_v1"

    samples: list[EvaluationSampleResult] = []
    excluded_non_retrieval = 0

    for idx, record in enumerate(filtered_records, start=1):
        question = record["question"]
        evaluation_id = record.get("evaluation_id") or f"{split}_{idx:03d}"

        # -------------------------------------------------------------
        # Leakage boundary: only question is passed to the Agent pipeline
        # -------------------------------------------------------------
        initial_state = initialize_agent_state(question)
        final_state = pipeline.graph.invoke(initial_state)

        final_response = final_state.get("final_response")
        if final_response is None:
            raise RuntimeError(f"Pipeline failed to produce a FinalResponse for {evaluation_id}.")

        final_evidence = final_state.get("retrieval_evidence", ())
        final_top5_chunk_ids = [c.chunk_id for c in final_evidence[:5]]
        retrieved_context = [
            {"doc_id": c.chunk_id, "text": c.content}
            for c in final_evidence
        ]

        # -------------------------------------------------------------
        # Evaluation layer reads Gold annotations only after generation
        # -------------------------------------------------------------
        category = record.get("category", "")
        gold_chunk_ids = list(record.get("gold_chunk_ids", []))
        gt_answer = record.get("gt_answer", "")

        is_non_retrieval = category in NON_RETRIEVAL_CATEGORIES
        if is_non_retrieval:
            excluded_non_retrieval += 1
            is_evaluable = False
            success_at_5 = False
            recall_at_5 = 0.0
        else:
            is_evaluable = True
            overlap = len(set(final_top5_chunk_ids) & set(gold_chunk_ids))
            success_at_5 = bool(overlap)
            recall_at_5 = overlap / len(gold_chunk_ids) if gold_chunk_ids else 0.0

        sample_result = EvaluationSampleResult(
            evaluation_id=evaluation_id,
            line_number=idx,
            question=question,
            split=split,
            category=category,
            gold_chunk_ids=gold_chunk_ids,
            gt_answer=gt_answer,
            final_response_status=final_response.status,
            generated_response=final_response.answer,
            final_top5_chunk_ids=final_top5_chunk_ids,
            retrieved_context=retrieved_context,
            rewrite_count=final_state.get("rewrite_count", 0),
            retrieval_pass_count=final_state.get("retrieval_pass_count", 1),
            success_at_5=success_at_5,
            recall_at_5=recall_at_5,
            is_retrieval_evaluable=is_evaluable,
        )
        samples.append(sample_result)

    evaluable_samples = [s for s in samples if s.is_retrieval_evaluable]
    successes = sum(1 for s in evaluable_samples if s.success_at_5)
    misses = len(evaluable_samples) - successes
    success_at_5 = successes / len(evaluable_samples) if evaluable_samples else 0.0
    recall_at_5 = (
        sum(s.recall_at_5 for s in evaluable_samples) / len(evaluable_samples)
        if evaluable_samples
        else 0.0
    )

    execution_result = FinalPipelineExecutionResult(
        split=split,
        system_commit=system_commit or get_system_commit(),
        kb_version=kb_version,
        pipeline_llm_model=settings.qwen_eval_model,
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
        total_samples=len(samples),
        retrieval_evaluable_samples=len(evaluable_samples),
        excluded_non_retrieval_samples=excluded_non_retrieval,
        successes_at_5=successes,
        misses_at_5=misses,
        success_at_5=success_at_5,
        recall_at_5=recall_at_5,
        samples=samples,
    )

    rag_results = map_evaluation_to_ragchecker_results(samples)
    return execution_result, rag_results
