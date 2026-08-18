from __future__ import annotations

import pytest

from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.models import RetrievalCandidate
from backend.app.retrieval.reranker import CrossEncoderReranker
from backend.app.retrieval.rrf import reciprocal_rank_fusion


def candidate(chunk_id: str, **changes: object) -> RetrievalCandidate:
    data: dict[str, object] = {
        "chunk_id": chunk_id,
        "content": f"Official evidence for {chunk_id}.",
        "source_id": "source-1",
        "source_title": "Official Care",
        "source_url": "https://example.com/care",
        "section_title": "Care",
    }
    data.update(changes)
    return RetrievalCandidate(**data)


def test_rrf_merges_ranked_lists_uses_rank_not_raw_score_and_preserves_trace():
    bm25 = [
        candidate("bm25-only", bm25_rank=1, bm25_score=0.001),
        candidate("shared", bm25_rank=2, bm25_score=0.0001),
    ]
    dense = [
        candidate("shared", dense_rank=1, dense_score=99.9),
        candidate("dense-only", dense_rank=2, dense_score=0.00001),
    ]

    result = reciprocal_rank_fusion(bm25, dense)
    by_id = {item.chunk_id: item for item in result}

    assert [item.chunk_id for item in result] == ["shared", "bm25-only", "dense-only"]
    assert by_id["shared"].bm25_rank == 2
    assert by_id["shared"].dense_rank == 1
    assert by_id["shared"].bm25_score == 0.0001
    assert by_id["shared"].dense_score == 99.9
    assert by_id["shared"].rrf_score == pytest.approx(1 / 62 + 1 / 61)
    assert by_id["shared"].content == "Official evidence for shared."
    assert len(by_id) == len(result)


def test_rrf_includes_single_path_candidates_top_30_and_has_deterministic_ties():
    bm25 = [candidate(f"b-{index:02d}", bm25_rank=index, bm25_score=float(index)) for index in range(1, 32)]
    dense = [candidate("a-tie", dense_rank=1, dense_score=10.0)]

    result = reciprocal_rank_fusion(bm25, dense)
    assert len(result) == 30
    assert {item.chunk_id for item in result}.issuperset({"b-01", "a-tie"})

    tied = reciprocal_rank_fusion(
        [candidate("z-tie", bm25_rank=1)],
        [candidate("a-tie", dense_rank=1)],
    )
    assert [item.chunk_id for item in tied] == ["a-tie", "z-tie"]


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[tuple[object, int, bool]] = []

    def predict(self, sentences, *, batch_size: int, show_progress_bar: bool):
        self.calls.append((sentences, batch_size, show_progress_bar))
        return self.scores


def test_reranker_uses_canonical_content_and_returns_top_five_without_mutating_evidence():
    candidates = [candidate(f"chunk-{index}", rrf_score=float(index)) for index in range(6)]
    model = FakeCrossEncoder([0.1, 0.9, 0.2, 0.8, 0.3, 0.7])
    reranker = CrossEncoderReranker(model, batch_size=8, top_k=5)

    result = reranker.rerank("How should I care for it?", candidates)

    assert model.calls[0] == (
        [("How should I care for it?", item.content) for item in candidates],
        8,
        False,
    )
    assert [item.chunk_id for item in result] == ["chunk-1", "chunk-3", "chunk-5", "chunk-4", "chunk-2"]
    assert [item.rerank_rank for item in result] == [1, 2, 3, 4, 5]
    assert result[0].rerank_score == 0.9
    assert result[0].rrf_score == 1.0
    assert result[0].content == candidates[1].content
    assert reranker.rerank("query", []) == []


class FakeBM25Retriever:
    def __init__(self, values: list[RetrievalCandidate]) -> None:
        self.values = values
        self.calls: list[tuple[str, dict]] = []

    def search(self, query_text: str, **kwargs):
        self.calls.append((query_text, kwargs))
        return self.values


class FakeDenseRetriever:
    def __init__(self, values: list[RetrievalCandidate]) -> None:
        self.values = values
        self.calls: list[str] = []

    def search(self, query_text: str):
        self.calls.append(query_text)
        return self.values


class FakeReranker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[RetrievalCandidate]]] = []

    def rerank(self, query: str, candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
        self.calls.append((query, candidates))
        return candidates[:5]


def test_hybrid_retriever_routes_query_inputs_and_uses_rrf_before_reranking():
    bm25 = FakeBM25Retriever([candidate("shared", bm25_rank=1, bm25_score=4.0)])
    dense = FakeDenseRetriever([candidate("shared", dense_rank=1, dense_score=0.8), candidate("dense", dense_rank=2)])
    reranker = FakeReranker()
    retriever = HybridRetriever(bm25, dense, reranker)

    result = retriever.retrieve(
        "中文原始问题",
        bm25_query_text="water repellency DWR",
        brand="GORE-TEX",
        technologies=["DWR"],
    )

    assert bm25.calls == [("water repellency DWR", {"brand": "GORE-TEX", "technologies": ["DWR"]})]
    assert dense.calls == ["中文原始问题"]
    assert reranker.calls[0][0] == "中文原始问题"
    assert reranker.calls[0][1][0].chunk_id == "shared"
    assert reranker.calls[0][1][0].bm25_rank == 1
    assert reranker.calls[0][1][0].dense_rank == 1
    assert result[0].chunk_id == "shared"


def test_retrieval_trace_is_observability_only_and_preserves_default_final_top_five():
    bm25 = FakeBM25Retriever([candidate("shared", bm25_rank=1, bm25_score=4.0)])
    dense = FakeDenseRetriever([candidate("shared", dense_rank=1, dense_score=0.8)])
    reranker = FakeReranker()
    retriever = HybridRetriever(bm25, dense, reranker)

    trace = retriever.retrieve_with_trace("original question")

    assert [item.chunk_id for item in trace.bm25_candidates] == ["shared"]
    assert [item.chunk_id for item in trace.dense_candidates] == ["shared"]
    assert [item.chunk_id for item in trace.rrf_candidates] == ["shared"]
    assert trace.reranked_candidates == retriever.retrieve("original question")
    assert bm25.calls == [
        ("original question", {"brand": None, "technologies": ()}),
        ("original question", {"brand": None, "technologies": ()}),
    ]
    assert dense.calls == ["original question", "original question"]
    assert [call[0] for call in reranker.calls] == ["original question", "original question"]


def test_hybrid_retriever_does_not_hide_retrieval_exceptions():
    class FailingDense:
        def search(self, query_text: str):
            raise RuntimeError("dense unavailable")

    retriever = HybridRetriever(FakeBM25Retriever([]), FailingDense(), FakeReranker())
    with pytest.raises(RuntimeError, match="dense unavailable"):
        retriever.retrieve("query")
