from __future__ import annotations

import pytest

from backend.app.query_analysis.analyzer import QueryAnalysisProviderError
from backend.app.query_analysis.evaluation import evaluate_integrated_dev
from backend.app.query_analysis.models import QueryAnalysisResult
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


def record(question: str, gold_chunk_ids: list[str], *, category: str = "washing") -> dict:
    return {
        "question": question,
        "gt_answer": "answer that must not enter Query Analysis",
        "gold_chunk_ids": gold_chunk_ids,
        "category": category,
        "kb_version": "kb_v1",
        "split": "dev",
    }


class FakeAnalyzer:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def analyze(self, question: str) -> QueryAnalysisResult:
        self.questions.append(question)
        return QueryAnalysisResult.model_validate(
            {
                "original_query": question,
                "lexical_terms_en": [" GORE-TEX ", "", "DWR"],
                "structured_query": {
                    "brand": "Arc'teryx",
                    "garment_type": "hardshell",
                    "technology": ["GORE-TEX"],
                    "issue_type": "water_repellency_loss",
                    "intent": "care_troubleshooting",
                    "care_stage": "restore_dwr",
                },
            }
        )


class FakeFrozenHybrid:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def retrieve_with_trace(self, original_query: str, **kwargs: object) -> RetrievalTrace:
        self.calls.append({"original_query": original_query, **kwargs})
        return RetrievalTrace(
            bm25_candidates=[candidate("bm25")],
            dense_candidates=[candidate("dense")],
            rrf_candidates=[candidate("rrf")],
            reranked_candidates=[candidate("gold-1")],
        )


class CategoryFrozenHybrid:
    def __init__(self, top5_by_question: dict[str, list[str]]) -> None:
        self.top5_by_question = top5_by_question

    def retrieve_with_trace(self, original_query: str, **kwargs: object) -> RetrievalTrace:
        return RetrievalTrace(
            bm25_candidates=[candidate("bm25")],
            dense_candidates=[candidate("dense")],
            rrf_candidates=[candidate("rrf")],
            reranked_candidates=[candidate(chunk_id) for chunk_id in self.top5_by_question[original_query]],
        )


def test_integrated_dev_evaluation_passes_only_question_to_analyzer_and_maps_frozen_inputs():
    question = "我的 GORE-TEX 冲锋衣不挂水珠了怎么办？"
    analyzer = FakeAnalyzer()
    retriever = FakeFrozenHybrid()

    result = evaluate_integrated_dev([record(question, ["gold-1"])], analyzer=analyzer, retriever=retriever)

    assert analyzer.questions == [question]
    assert retriever.calls == [
        {
            "original_query": question,
            "bm25_query_text": "GORE-TEX DWR",
            "brand": "Arc'teryx",
            "technologies": ("GORE-TEX",),
        }
    ]
    assert result.evaluation.retrieval_evaluable_records == 1
    assert result.evaluation.successes_at_5 == 1
    assert result.evaluation.recall_at_5 == 1.0
    assert result.query_artifacts[0].original_query == question
    assert result.query_artifacts[0].adapter == {
        "bm25_query_text": "GORE-TEX DWR",
        "brand": "Arc'teryx",
        "technologies": ("GORE-TEX",),
    }


def test_non_retrieval_records_do_not_call_analyzer_or_retriever():
    analyzer = FakeAnalyzer()
    retriever = FakeFrozenHybrid()

    result = evaluate_integrated_dev(
        [record("need more information", [], category="missing_information")],
        analyzer=analyzer,
        retriever=retriever,
    )

    assert analyzer.questions == []
    assert retriever.calls == []
    assert result.evaluation.retrieval_evaluable_records == 0
    assert result.evaluation.excluded_non_retrieval_records == 1


def test_category_and_gold_fields_do_not_enter_query_analysis_or_retrieval():
    analyzer = FakeAnalyzer()
    retriever = FakeFrozenHybrid()
    input_record = record("question only", ["gold-1"], category="washing")
    input_record["expected_answer"] = "must remain evaluator-only"

    evaluate_integrated_dev([input_record], analyzer=analyzer, retriever=retriever)

    assert analyzer.questions == ["question only"]
    assert retriever.calls[0]["original_query"] == "question only"
    assert "gold-1" not in str(retriever.calls[0])
    assert "washing" not in str(retriever.calls[0])


def test_category_recall_uses_mean_per_query_and_excludes_non_retrieval_categories():
    analyzer = FakeAnalyzer()
    records = [
        record("wash hit", ["wash-gold"], category="washing"),
        record("wash partial", ["wash-a", "wash-b"], category="washing"),
        record("dry miss", ["dry-gold"], category="drying"),
        record("excluded", [], category="missing_information"),
    ]
    retriever = CategoryFrozenHybrid(
        {
            "wash hit": ["wash-gold"],
            "wash partial": ["wash-a"],
            "dry miss": ["other"],
        }
    )

    result = evaluate_integrated_dev(records, analyzer=analyzer, retriever=retriever)

    assert [category.as_dict() for category in result.category_recall_at_5] == [
        {"category": "drying", "evaluable_samples": 1, "recall_at_5": 0.0},
        {"category": "washing", "evaluable_samples": 2, "recall_at_5": 0.75},
    ]
    assert result.evaluation.recall_at_5 == 0.5


def test_empty_retrieval_evaluable_set_has_no_category_metrics():
    result = evaluate_integrated_dev(
        [record("excluded", [], category="insufficient_evidence")],
        analyzer=FakeAnalyzer(),
        retriever=FakeFrozenHybrid(),
    )

    assert result.evaluation.retrieval_evaluable_records == 0
    assert result.category_recall_at_5 == []


def test_provider_failure_is_not_scored_as_a_retrieval_miss():
    class FailingAnalyzer:
        def analyze(self, question: str) -> QueryAnalysisResult:
            raise QueryAnalysisProviderError("provider unavailable")

    with pytest.raises(QueryAnalysisProviderError, match="provider unavailable"):
        evaluate_integrated_dev(
            [record("question", ["gold-1"])],
            analyzer=FailingAnalyzer(),
            retriever=FakeFrozenHybrid(),
        )


def test_integrated_evaluation_rejects_non_dev_records():
    non_dev = record("test question", ["gold-1"])
    non_dev["split"] = "test"

    with pytest.raises(ValueError, match="DEV records only"):
        evaluate_integrated_dev([non_dev], analyzer=FakeAnalyzer(), retriever=FakeFrozenHybrid())
