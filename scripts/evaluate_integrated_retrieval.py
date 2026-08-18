"""Run the Stage 8B DEV-only Query Analysis → frozen Retriever evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.knowledge.embedding import E5Embedder
from backend.app.query_analysis.analyzer import QueryAnalyzer
from backend.app.query_analysis.evaluation import evaluate_integrated_dev
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.reranker import CrossEncoderReranker
from backend.app.runtime import create_elasticsearch_client


DEFAULT_DATASET = ROOT / "data/evaluation/golden_dataset.jsonl"
DEFAULT_OUTPUT = ROOT / "results/stage8b_dev_integrated_baseline.json"


def _read_dev_records(path: Path) -> list[dict]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [record for record in records if record.get("split") == "dev"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    settings = get_settings()
    client = create_elasticsearch_client(settings)
    try:
        embedder = E5Embedder(model_name=settings.embedding_model, device=settings.embedding_device)
        retriever = HybridRetriever(
            BM25Retriever(client, settings.es_index_name, top_k=settings.bm25_top_k),
            DenseRetriever(
                client,
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
        result = evaluate_integrated_dev(
            _read_dev_records(args.dataset),
            analyzer=QueryAnalyzer.from_settings(settings),
            retriever=retriever,
        )
    finally:
        client.close()

    serialized = json.dumps(result.as_dict(), ensure_ascii=False, indent=2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "split": result.evaluation.split,
                "total_records": result.evaluation.total_records,
                "retrieval_evaluable_records": result.evaluation.retrieval_evaluable_records,
                "excluded_non_retrieval_records": result.evaluation.excluded_non_retrieval_records,
                "successes_at_5": result.evaluation.successes_at_5,
                "success_at_5": result.evaluation.success_at_5,
                "recall_at_5": result.evaluation.recall_at_5,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
