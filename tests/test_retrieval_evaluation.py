from __future__ import annotations

from backend.app.retrieval.evaluation import evaluate_retriever, recalculate_saved_metrics
from backend.app.retrieval.hybrid import RetrievalTrace
from backend.app.retrieval.models import RetrievalCandidate


def candidate(chunk_id: str) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        content=chunk_id,
        source_id="source",
        source_title="title",
        source_url="https://example.com",
        section_title="section",
    )


class FakeRetriever:
    def __init__(self, top5_by_question: dict[str, list[str]]) -> None:
        self.top5_by_question = top5_by_question
        self.calls: list[tuple[str, str | None]] = []

    def retrieve_with_trace(self, original_query: str, *, bm25_query_text: str | None = None) -> RetrievalTrace:
        self.calls.append((original_query, bm25_query_text))
        final = [candidate(chunk_id) for chunk_id in self.top5_by_question[original_query]]
        return RetrievalTrace(
            bm25_candidates=[candidate("bm25-gold")],
            dense_candidates=[candidate("dense-gold")],
            rrf_candidates=[candidate("rrf-gold")],
            reranked_candidates=final,
        )


def record(question: str, gold_chunk_ids: list[str], *, split: str = "dev", category: str = "washing") -> dict:
    return {
        "question": question,
        "gt_answer": "answer",
        "gold_chunk_ids": gold_chunk_ids,
        "category": category,
        "kb_version": "kb_v1",
        "split": split,
    }


def test_success_and_recall_at_five_handle_single_and_multiple_gold_samples():
    records = [
        record("single hit", ["gold-1"]),
        record("single miss", ["gold-2"]),
        record("two gold partial", ["gold-3", "gold-4"]),
        record("two gold full", ["gold-5", "gold-6"]),
        record("negative", [], category="missing_information"),
        record("test hit", ["gold-test"], split="test"),
    ]
    retriever = FakeRetriever(
        {
            "single hit": ["x", "gold-1"],
            "single miss": ["x"],
            "two gold partial": ["gold-4"],
            "two gold full": ["gold-5", "gold-6"],
            "test hit": ["gold-test"],
        }
    )

    result = evaluate_retriever(records, retriever, split="dev")

    assert result.total_records == 5
    assert result.retrieval_evaluable_records == 4
    assert result.excluded_non_retrieval_records == 1
    assert (result.successes_at_5, result.misses_at_5, result.success_at_5) == (3, 1, 3 / 4)
    assert result.recall_at_5 == 2.5 / 4
    assert [sample.success_at_5 for sample in result.samples] == [True, False, True, True]
    assert [sample.recall_at_5 for sample in result.samples] == [1.0, 0.0, 0.5, 1.0]
    assert retriever.calls == [
        ("single hit", None),
        ("single miss", None),
        ("two gold partial", None),
        ("two gold full", None),
    ]


def test_evaluator_compares_gold_only_after_retriever_returns_top_five():
    records = [record("question", ["gold"])]
    retriever = FakeRetriever({"question": ["gold"]})

    result = evaluate_retriever(records, retriever, split="dev")

    assert result.samples[0].retrieved_top5_chunk_ids == ["gold"]
    assert result.samples[0].gold_chunk_ids == ["gold"]
    assert result.samples[0].success_at_5 is True
    assert result.samples[0].recall_at_5 == 1.0


def test_saved_top_five_metrics_are_recomputed_without_retriever_execution():
    metrics = recalculate_saved_metrics(
        {
            "samples": [
                {"gold_chunk_ids": ["a"], "retrieved_top5_chunk_ids": ["a"]},
                {"gold_chunk_ids": ["b", "c"], "retrieved_top5_chunk_ids": ["c"]},
                {"gold_chunk_ids": ["d"], "retrieved_top5_chunk_ids": ["x"]},
            ]
        }
    )

    assert metrics == {
        "retrieval_evaluable_records": 3,
        "successes_at_5": 2,
        "misses_at_5": 1,
        "success_at_5": 2 / 3,
        "recall_at_5": 0.5,
    }
