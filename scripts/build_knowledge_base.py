"""Build, embed, and index the complete local knowledge base."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.knowledge.chunker import chunk_documents, load_tokenizer
from backend.app.knowledge.cleaner import clean_documents
from backend.app.knowledge.embedding import E5Embedder
from backend.app.knowledge.indexer import bulk_index, build_mapping, ensure_index
from backend.app.knowledge.loader import load_sources
from backend.app.knowledge.metadata import enrich_chunk
from backend.app.knowledge.models import ChunkRecord
from backend.app.runtime import create_elasticsearch_client

OUTPUT = ROOT / "data/processed/chunks.jsonl"


def _build_records(settings) -> tuple[list[dict], float]:
    tokenizer = load_tokenizer()
    documents = clean_documents(load_sources())
    chunks = chunk_documents(
        documents,
        tokenizer,
        max_tokens=settings.max_chunk_tokens,
        overlap_tokens=settings.fallback_overlap_tokens,
    )
    enriched = [enrich_chunk(ChunkRecord.model_validate(chunk.model_dump(mode="json"))) for chunk in chunks]
    embedder = E5Embedder(model_name=settings.embedding_model, device=settings.embedding_device)
    vectors, seconds = embedder.encode(
        [record["embedding_text"] for record in enriched],
        batch_size=settings.embedding_batch_size,
    )
    for record, vector in zip(enriched, vectors):
        record["embedding"] = vector
    return enriched, seconds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.es_index_name or "*" in settings.es_index_name:
        raise ValueError("ES_INDEX_NAME must be one exact index name")
    records, seconds = _build_records(settings)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")

    client = create_elasticsearch_client(settings)
    try:
        if args.rebuild:
            client.indices.delete(index=settings.es_index_name, ignore_unavailable=True)
            client.indices.create(
                index=settings.es_index_name,
                **build_mapping(
                    dims=settings.embedding_dim,
                    shards=settings.es_number_of_shards,
                    replicas=settings.es_number_of_replicas,
                ),
            )
        else:
            ensure_index(
                client,
                settings.es_index_name,
                dims=settings.embedding_dim,
                shards=settings.es_number_of_shards,
                replicas=settings.es_number_of_replicas,
            )
        indexed = bulk_index(client, settings.es_index_name, records)
        count = client.count(index=settings.es_index_name)["count"]
    finally:
        client.close()
    print(json.dumps({
        "source_count": len({record["source_id"] for record in records}),
        "chunk_count": len(records),
        "embedding_count": len(records),
        "embedding_dim": len(records[0]["embedding"]) if records else 0,
        "embedding_seconds": round(seconds, 2),
        "indexed": indexed,
        "es_document_count": count,
        "rebuild": args.rebuild,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
