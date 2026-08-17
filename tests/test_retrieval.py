import pytest
from backend.app.retrieval.bm25 import BM25Retriever, build_bm25_query
from backend.app.retrieval.dense import DenseRetriever


SOURCE = {
    "chunk_id": "goretex-001/section/000",
    "content": "Wash with a small amount of liquid detergent.",
    "source_id": "goretex-001",
    "source_title": "GORE-TEX Care",
    "source_url": "https://example.com/care",
    "section_title": "Washing",
}


class FakeClient:
    def __init__(self, hits=None, error=None):
        self.hits = hits if hits is not None else []
        self.error = error
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return {"hits": {"hits": self.hits}}


class FakeEmbedder:
    def __init__(self, vector):
        self.vector = vector
        self.queries = []

    def encode_query(self, query_text):
        self.queries.append(query_text)
        return self.vector


def hit(score=12.5):
    return {"_source": SOURCE, "_score": score}


def test_bm25_dsl_uses_formal_multifield_boosts_and_optional_metadata_boosts():
    query = build_bm25_query("GORE-TEX DWR", brand="GORE-TEX", technologies=["DWR"])
    body = query["bool"]
    multi_match = body["must"][0]["multi_match"]
    assert multi_match["query"] == "GORE-TEX DWR"
    assert multi_match["fields"] == [
        "content^1.0",
        "source_title^1.5",
        "section_title^1.5",
        "normalized_terms^1.5",
    ]
    assert {"term": {"brand": {"value": "GORE-TEX", "boost": 1.5}}} in body["should"]
    assert {"term": {"technology": {"value": "DWR", "boost": 2.0}}} in body["should"]


def test_bm25_returns_top_k_candidates_with_real_raw_score_and_one_based_rank():
    client = FakeClient([hit(12.5), hit(8.25)])
    candidates = BM25Retriever(client, "fashion_care_kb_v1").search("DWR")

    assert len(candidates) == 2
    assert candidates[0].chunk_id == SOURCE["chunk_id"]
    assert candidates[0].content == SOURCE["content"]
    assert candidates[0].source_url == SOURCE["source_url"]
    assert candidates[0].bm25_score == 12.5
    assert candidates[0].bm25_rank == 1
    assert candidates[0].dense_score is None
    assert candidates[1].bm25_rank == 2
    assert client.calls[0]["size"] == 20


def test_bm25_empty_hits_remain_empty_and_es_exceptions_propagate():
    assert BM25Retriever(FakeClient(), "fashion_care_kb_v1").search("DWR") == []
    with pytest.raises(RuntimeError, match="ES unavailable"):
        BM25Retriever(FakeClient(error=RuntimeError("ES unavailable")), "fashion_care_kb_v1").search("DWR")


def test_dense_uses_query_embedder_and_knn_baseline_with_one_based_ranks():
    client = FakeClient([hit(0.93), hit(0.81)])
    embedder = FakeEmbedder([0.1] * 384)
    candidates = DenseRetriever(client, embedder, "fashion_care_kb_v1").search("我的冲锋衣不挂水珠")

    assert embedder.queries == ["我的冲锋衣不挂水珠"]
    assert candidates[0].dense_score == 0.93
    assert candidates[0].dense_rank == 1
    assert candidates[0].bm25_score is None
    assert candidates[1].dense_rank == 2
    knn = client.calls[0]["knn"]
    assert knn["field"] == "embedding"
    assert knn["k"] == 20
    assert knn["num_candidates"] == 100
    assert len(knn["query_vector"]) == 384
    assert client.calls[0]["size"] == 20


def test_dense_empty_hits_and_wrong_embedding_dimension_are_not_hidden():
    empty_client = FakeClient()
    assert DenseRetriever(empty_client, FakeEmbedder([0.1] * 384), "fashion_care_kb_v1").search("DWR") == []

    with pytest.raises(ValueError, match="dimension"):
        DenseRetriever(FakeClient(), FakeEmbedder([0.1] * 383), "fashion_care_kb_v1").search("DWR")

    with pytest.raises(RuntimeError, match="ES unavailable"):
        DenseRetriever(
            FakeClient(error=RuntimeError("ES unavailable")),
            FakeEmbedder([0.1] * 384),
            "fashion_care_kb_v1",
        ).search("DWR")
