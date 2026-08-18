"""Run the Stage 14 Final Pipeline + RAGChecker evaluation (TEST-only)."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.evaluation import (
    build_final_evaluation_pipeline,
    build_final_metrics,
    evaluate_final_test,
    run_ragchecker_evaluation,
    run_stage14_preflight,
)
from backend.app.knowledge.embedding import E5Embedder
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.reranker import CrossEncoderReranker
from backend.app.runtime import create_elasticsearch_client

DEFAULT_DATASET = ROOT / "data/evaluation/golden_dataset.jsonl"
DEFAULT_PIPELINE_OUTPUT = ROOT / "results/stage14_final_pipeline.json"
DEFAULT_RAGCHECKER_OUTPUT = ROOT / "results/ragchecker_results.json"
DEFAULT_METRICS_OUTPUT = ROOT / "results/final_metrics.json"


def _read_records(path: Path, split: str = "test") -> list[dict]:
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [r for r in records if r.get("split") == split]


def run_stage14_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET,
    split: str = "test",
    pipeline_output_path: Path = DEFAULT_PIPELINE_OUTPUT,
    ragchecker_output_path: Path = DEFAULT_RAGCHECKER_OUTPUT,
    metrics_output_path: Path = DEFAULT_METRICS_OUTPUT,
    official_run_id: str | None = None,
    preflight_only: bool = False,
    require_clean_git: bool | None = None,
) -> dict[str, object]:
    """Execute the complete Stage 14 evaluation workflow with preflight gating (TEST-only).

    Provenance Contract:
    - Official full runs (`preflight_only=False`) strictly enforce `require_clean_git=True`.
    - Preflight-only diagnostic runs default to `require_clean_git=False` unless explicitly requested.
    """
    if split != "test":
        raise ValueError(
            f"Stage 14 official runner accepts TEST split only; received split='{split}'."
        )

    # Enforce strict clean Git provenance on official runs by default
    enforce_clean_git = True if require_clean_git is None and not preflight_only else bool(require_clean_git)

    settings = get_settings()

    # -------------------------------------------------------------
    # 1. Real Infrastructure Preflight Check (Gating before dataset access)
    # -------------------------------------------------------------
    preflight_result = run_stage14_preflight(
        settings=settings,
        pipeline_output_path=pipeline_output_path,
        ragchecker_output_path=ragchecker_output_path,
        metrics_output_path=metrics_output_path,
        require_clean_git=enforce_clean_git,
    )

    if preflight_only:
        return preflight_result

    # -------------------------------------------------------------
    # 2. Pipeline Execution (Only runs after preflight succeeds)
    # -------------------------------------------------------------
    es_client = create_elasticsearch_client(settings)
    run_id = official_run_id or f"stage14_{uuid.uuid4().hex[:12]}"
    run_timestamp = datetime.now(timezone.utc).isoformat()

    try:
        embedder = E5Embedder(
            model_name=settings.embedding_model,
            device=settings.embedding_device,
        )
        retriever = HybridRetriever(
            BM25Retriever(es_client, settings.es_index_name, top_k=settings.bm25_top_k),
            DenseRetriever(
                es_client,
                embedder,
                settings.es_index_name,
                top_k=settings.dense_top_k,
                num_candidates=settings.dense_num_candidates,
                embedding_dim=settings.embedding_dim,
            ),
            CrossEncoderReranker.load(
                settings.reranker_model,
                device=settings.reranker_device,
                batch_size=settings.reranker_batch_size,
                top_k=settings.rerank_top_k,
            ),
            rrf_k=settings.rrf_k,
            rrf_top_n=settings.rrf_top_n,
            bm25_weight=settings.bm25_rrf_weight,
            dense_weight=settings.dense_rrf_weight,
        )

        pipeline = build_final_evaluation_pipeline(
            settings=settings,
            retriever=retriever,
        )

        records = _read_records(dataset_path, split="test")
        execution_result, rag_results = evaluate_final_test(
            records,
            pipeline=pipeline,
            settings=settings,
            split="test",
        )

        pipeline_output_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline_output_path.write_text(
            json.dumps(execution_result.as_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        ragchecker_metrics = run_ragchecker_evaluation(
            rag_results,
            settings=settings,
            save_path=str(ragchecker_output_path),
        )

        final_metrics = build_final_metrics(
            system_commit=execution_result.system_commit,
            kb_version=execution_result.kb_version,
            test_samples=execution_result.total_samples,
            retrieval_evaluable_samples=execution_result.retrieval_evaluable_samples,
            embedding_model=execution_result.embedding_model,
            reranker_model=execution_result.reranker_model,
            pipeline_llm_model=execution_result.pipeline_llm_model,
            ragchecker_extractor_model=settings.ragchecker_extractor_model,
            ragchecker_checker_model=settings.ragchecker_checker_model,
            success_at_5=execution_result.success_at_5,
            recall_at_5=execution_result.recall_at_5,
            ragchecker_metrics=ragchecker_metrics,
            official_run_id=run_id,
            timestamp=run_timestamp,
        )

        metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_output_path.write_text(
            json.dumps(final_metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return final_metrics
    finally:
        es_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 14 Final Evaluation Runner (TEST-only)")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--pipeline-output", type=Path, default=DEFAULT_PIPELINE_OUTPUT)
    parser.add_argument("--ragchecker-output", type=Path, default=DEFAULT_RAGCHECKER_OUTPUT)
    parser.add_argument("--metrics-output", type=Path, default=DEFAULT_METRICS_OUTPUT)
    parser.add_argument("--official-run-id", type=str, default=None)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--require-clean-git",
        action="store_true",
        default=None,
        help="Explicitly enforce clean Git provenance (mandatory on official full runs)",
    )
    args = parser.parse_args()

    results = run_stage14_evaluation(
        dataset_path=args.dataset,
        split="test",
        pipeline_output_path=args.pipeline_output,
        ragchecker_output_path=args.ragchecker_output,
        metrics_output_path=args.metrics_output,
        official_run_id=args.official_run_id,
        preflight_only=args.preflight_only,
        require_clean_git=args.require_clean_git,
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
