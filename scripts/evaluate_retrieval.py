"""Run standalone Hybrid Retriever Success@5 and Recall@5 evaluation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.knowledge.embedding import E5Embedder
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.dense import DenseRetriever
from backend.app.retrieval.evaluation import evaluate_retriever
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.reranker import CrossEncoderReranker
from backend.app.runtime import create_elasticsearch_client


DEFAULT_DATASET = ROOT / "data/evaluation/golden_dataset.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _config_snapshot() -> dict[str, object]:
    settings = get_settings()
    return {
        "bm25_top_k": settings.bm25_top_k,
        "bm25_field_boosts": {
            "content": 1.0,
            "source_title": 1.5,
            "section_title": 1.5,
            "normalized_terms": 1.5,
            "brand": 1.5,
            "technology": 2.0,
        },
        "dense_top_k": settings.dense_top_k,
        "dense_num_candidates": settings.dense_num_candidates,
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "rrf_k": settings.rrf_k,
        "rrf_top_n": settings.rrf_top_n,
        "bm25_rrf_weight": settings.bm25_rrf_weight,
        "dense_rrf_weight": settings.dense_rrf_weight,
        "reranker_model": settings.reranker_model,
        "reranker_device": settings.reranker_device,
        "reranker_batch_size": settings.reranker_batch_size,
        "rerank_top_k": settings.rerank_top_k,
        "query_contract": {
            "original_query": "frozen Golden Dataset question",
            "bm25_query_text": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
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
        payload = {
            "retrieval_config": _config_snapshot(),
            "result": evaluate_retriever(_read_jsonl(args.dataset), retriever, split=args.split).as_dict(),
        }
    finally:
        client.close()

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
