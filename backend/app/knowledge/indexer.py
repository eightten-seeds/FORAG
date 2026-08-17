from __future__ import annotations

from elasticsearch import Elasticsearch, helpers


def build_mapping() -> dict:
    return {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {"properties": {
            "chunk_id": {"type": "keyword"}, "parent_doc_id": {"type": "keyword"}, "document_id": {"type": "keyword"},
            "source_id": {"type": "keyword"}, "chunk_order": {"type": "integer"},
            "content": {"type": "text"}, "source_title": {"type": "text"}, "section_title": {"type": "text"},
            "source_url": {"type": "keyword"}, "brand": {"type": "keyword"},
            "garment_type": {"type": "keyword"}, "technology": {"type": "keyword"}, "care_stage": {"type": "keyword"},
            "normalized_terms": {"type": "text"}, "embedding_text": {"type": "text"},
            "content_hash": {"type": "keyword"}, "kb_version": {"type": "keyword"},
            "embedding": {"type": "dense_vector", "dims": 384, "index": True, "similarity": "cosine"},
        }}
    }


def ensure_index(client: Elasticsearch, index_name: str) -> None:
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, **build_mapping())


def bulk_index(client: Elasticsearch, index_name: str, records: list[dict]) -> int:
    actions = ({"_index": index_name, "_id": record["chunk_id"], "_source": record} for record in records)
    success, _ = helpers.bulk(client, actions, refresh="wait_for")
    return int(success)
