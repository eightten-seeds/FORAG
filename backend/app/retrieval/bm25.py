from __future__ import annotations

from collections.abc import Sequence

from elasticsearch import Elasticsearch

from backend.app.retrieval.models import RetrievalCandidate


RETRIEVAL_SOURCE_FIELDS = (
    "chunk_id",
    "content",
    "source_id",
    "source_title",
    "source_url",
    "section_title",
)

CONTENT_BOOST = 1.0
TITLE_BOOST = 1.5
SECTION_BOOST = 1.5
NORMALIZED_TERMS_BOOST = 1.5
BRAND_BOOST = 1.5
TECHNOLOGY_BOOST = 2.0


def build_bm25_query(
    query_text: str,
    *,
    brand: str | None = None,
    technologies: Sequence[str] = (),
) -> dict:
    """Build the ES BM25 query for the frozen KB mapping.

    Metadata is optional because Stage 5A accepts a direct query text before
    Query Analysis exists. When supplied by a later caller it only boosts,
    never hard-filters, candidate documents.
    """
    cleaned_query = query_text.strip()
    if not cleaned_query:
        raise ValueError("query_text must not be empty")

    multi_match = {
        "multi_match": {
            "query": cleaned_query,
            "fields": [
                f"content^{CONTENT_BOOST}",
                f"source_title^{TITLE_BOOST}",
                f"section_title^{SECTION_BOOST}",
                f"normalized_terms^{NORMALIZED_TERMS_BOOST}",
            ],
            "type": "best_fields",
        }
    }
    should: list[dict] = []
    if brand:
        should.append({"term": {"brand": {"value": brand, "boost": BRAND_BOOST}}})
    for technology in technologies:
        if technology.strip():
            should.append(
                {"term": {"technology": {"value": technology.strip(), "boost": TECHNOLOGY_BOOST}}}
            )

    if not should:
        return multi_match
    return {"bool": {"must": [multi_match], "should": should}}


def bm25_candidate_from_hit(hit: dict, *, rank: int) -> RetrievalCandidate:
    source = hit["_source"]
    return RetrievalCandidate(
        chunk_id=source["chunk_id"],
        content=source["content"],
        source_id=source["source_id"],
        source_title=source["source_title"],
        source_url=source["source_url"],
        section_title=source["section_title"],
        bm25_score=float(hit["_score"]),
        bm25_rank=rank,
    )


class BM25Retriever:
    """Real Elasticsearch BM25 retrieval over the frozen KB index."""

    def __init__(self, client: Elasticsearch, index_name: str, *, top_k: int = 20) -> None:
        self.client = client
        self.index_name = index_name
        self.top_k = top_k

    def search(
        self,
        query_text: str,
        *,
        brand: str | None = None,
        technologies: Sequence[str] = (),
    ) -> list[RetrievalCandidate]:
        response = self.client.search(
            index=self.index_name,
            query=build_bm25_query(query_text, brand=brand, technologies=technologies),
            size=self.top_k,
            source=list(RETRIEVAL_SOURCE_FIELDS),
        )
        return [
            bm25_candidate_from_hit(hit, rank=rank)
            for rank, hit in enumerate(response["hits"]["hits"], start=1)
        ]
