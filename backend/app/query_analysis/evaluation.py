"""DEV-only integration of Query Analysis with the frozen Hybrid Retriever."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from backend.app.query_analysis.adapter import FrozenRetrieverInputs, to_frozen_retriever_inputs
from backend.app.query_analysis.models import QueryAnalysisResult
from backend.app.retrieval.evaluation import EvaluationResult, evaluate_retriever
from backend.app.retrieval.hybrid import RetrievalTrace


class Analyzer(Protocol):
    def analyze(self, question: str) -> QueryAnalysisResult: ...


class FrozenHybrid(Protocol):
    def retrieve_with_trace(
        self,
        original_query: str,
        *,
        bm25_query_text: str | None = None,
        brand: str | None = None,
        technologies: tuple[str, ...] = (),
    ) -> RetrievalTrace: ...


@dataclass(frozen=True)
class IntegratedQueryArtifact:
    """Query-only analysis artifacts retained alongside post-retrieval metrics."""

    original_query: str
    lexical_terms_en: list[str]
    structured_query: dict[str, object]
    adapter: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CategoryRecallAt5:
    """Stage 13 category aggregation over frozen per-query retrieval metrics."""

    category: str
    evaluable_samples: int
    recall_at_5: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IntegratedEvaluationResult:
    """Frozen retrieval metrics plus the upstream artifacts that produced them."""

    evaluation: EvaluationResult
    query_artifacts: list[IntegratedQueryArtifact]
    category_recall_at_5: list[CategoryRecallAt5]

    def as_dict(self) -> dict[str, object]:
        return {
            "result": self.evaluation.as_dict(),
            "query_artifacts": [artifact.as_dict() for artifact in self.query_artifacts],
            "category_recall_at_5": [
                category.as_dict() for category in self.category_recall_at_5
            ],
        }


class QueryAnalysisIntegratedRetriever:
    """Question-only upstream adapter for the frozen Hybrid Retriever."""

    def __init__(self, analyzer: Analyzer, retriever: FrozenHybrid) -> None:
        self._analyzer = analyzer
        self._retriever = retriever
        self.query_artifacts: list[IntegratedQueryArtifact] = []

    def retrieve_with_trace(
        self,
        original_query: str,
        *,
        bm25_query_text: str | None = None,
    ) -> RetrievalTrace:
        if bm25_query_text is not None:
            raise ValueError("Integrated retrieval owns bm25_query_text via Query Analysis.")

        analysis = self._analyzer.analyze(original_query)
        adapter = to_frozen_retriever_inputs(analysis)
        self.query_artifacts.append(
            IntegratedQueryArtifact(
                original_query=analysis.original_query,
                lexical_terms_en=analysis.lexical_terms_en,
                structured_query=analysis.structured_query.model_dump(),
                adapter=adapter.model_dump(),
            )
        )
        return self._retriever.retrieve_with_trace(
            original_query=analysis.original_query,
            bm25_query_text=adapter.bm25_query_text,
            brand=adapter.brand,
            technologies=adapter.technologies,
        )


def evaluate_integrated_dev(
    records: list[dict],
    *,
    analyzer: Analyzer,
    retriever: FrozenHybrid,
) -> IntegratedEvaluationResult:
    """Evaluate only DEV records using Stage 5C's frozen metric implementation."""

    if any(record.get("split") != "dev" for record in records):
        raise ValueError("Stage 8B integrated evaluation accepts DEV records only.")

    integrated = QueryAnalysisIntegratedRetriever(analyzer, retriever)
    evaluation = evaluate_retriever(records, integrated, split="dev")
    categories_by_line = {
        line_number: record["category"]
        for line_number, record in enumerate(records, start=1)
        if record.get("split") == "dev"
        and record.get("category") not in {"insufficient_evidence", "missing_information"}
    }
    recalls_by_category: dict[str, list[float]] = {}
    for sample in evaluation.samples:
        category = categories_by_line[sample.line_number]
        recalls_by_category.setdefault(category, []).append(sample.recall_at_5)

    category_recall_at_5 = [
        CategoryRecallAt5(
            category=category,
            evaluable_samples=len(recalls),
            recall_at_5=sum(recalls) / len(recalls),
        )
        for category, recalls in sorted(recalls_by_category.items())
    ]
    return IntegratedEvaluationResult(
        evaluation=evaluation,
        query_artifacts=integrated.query_artifacts,
        category_recall_at_5=category_recall_at_5,
    )
