"""Enrich chunks, generate real E5 vectors, and optionally index them."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import get_settings
from backend.app.knowledge.embedding import E5Embedder
from backend.app.knowledge.indexer import bulk_index, ensure_index
from backend.app.knowledge.metadata import enrich_chunk
from backend.app.knowledge.models import ChunkRecord
from backend.app.runtime import create_elasticsearch_client

CHUNKS = ROOT / "data/processed/chunks.jsonl"


def main() -> None:
    records = [json.loads(line) for line in CHUNKS.read_text(encoding="utf-8").splitlines() if line.strip()]
    enriched = [enrich_chunk(ChunkRecord.model_validate(r)) for r in records]
    embedder = E5Embedder()
    vectors, seconds = embedder.encode([r["embedding_text"] for r in enriched])
    for record, vector in zip(enriched, vectors):
        record["embedding"] = vector
    CHUNKS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in enriched), encoding="utf-8")
    settings = get_settings()
    client = create_elasticsearch_client(settings)
    try:
        ensure_index(client, settings.es_index_name)
        indexed = bulk_index(client, settings.es_index_name, enriched)
    finally:
        client.close()
    print(json.dumps({"embedding_count": len(vectors), "dimension": len(vectors[0]) if vectors else 0, "seconds": round(seconds, 2), "indexed": indexed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
