"""Leakage-safe Success@5 and Recall@5 evaluation for the Hybrid Retriever."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from backend.app.retrieval.hybrid import RetrievalTrace


NON_RETRIEVAL_CATEGORIES = frozenset({"insufficient_evidence", "missing_information"})
VALID_SPLITS = frozenset({"dev", "test"})


class TracedRetriever(Protocol):
    def retrieve_with_trace(
        self,
        original_query: str,
        *,
        bm25_query_text: str | None = None,
    ) -> RetrievalTrace: ...


@dataclass(frozen=True)
class EvaluationSample:
    line_number: int
    question: str
    gold_chunk_ids: list[str]
    bm25_top_chunk_ids: list[str]
    dense_top_chunk_ids: list[str]
    rrf_top_chunk_ids: list[str]
    retrieved_top5_chunk_ids: list[str]
    success_at_5: bool
    recall_at_5: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationResult:
    split: str
    total_records: int
    retrieval_evaluable_records: int
    excluded_non_retrieval_records: int
    successes_at_5: int
    misses_at_5: int
    success_at_5: float
    recall_at_5: float
    samples: list[EvaluationSample]

    def as_dict(self) -> dict:
        result = asdict(self)
        result["samples"] = [sample.as_dict() for sample in self.samples]
        return result


def _candidate_ids(trace: RetrievalTrace) -> tuple[list[str], list[str], list[str], list[str]]:
    return (
        [candidate.chunk_id for candidate in trace.bm25_candidates],
        [candidate.chunk_id for candidate in trace.dense_candidates],
        [candidate.chunk_id for candidate in trace.rrf_candidates],
        [candidate.chunk_id for candidate in trace.reranked_candidates],
    )


def _metrics(samples: list[EvaluationSample]) -> tuple[int, int, float, float]:
    successes = sum(sample.success_at_5 for sample in samples)
    evaluable = len(samples)
    recall = sum(sample.recall_at_5 for sample in samples) / evaluable if evaluable else 0.0
    return successes, evaluable - successes, successes / evaluable if evaluable else 0.0, recall


def recalculate_saved_metrics(result: dict) -> dict[str, float | int]:
    """Recompute metrics from saved per-query Top5 output without retrieval.

    This is used for metric-correction reporting. It does not instantiate a
    retriever, call Elasticsearch, or consume any fields other than stored
    Gold IDs and retrieved Top5 IDs.
    """
    samples = result["samples"]
    successes = 0
    recall_sum = 0.0
    for sample in samples:
        gold_ids = set(sample["gold_chunk_ids"])
        retrieved_ids = set(sample["retrieved_top5_chunk_ids"])
        overlap = len(gold_ids & retrieved_ids)
        successes += bool(overlap)
        recall_sum += overlap / len(gold_ids)
    evaluable = len(samples)
    return {
        "retrieval_evaluable_records": evaluable,
        "successes_at_5": successes,
        "misses_at_5": evaluable - successes,
        "success_at_5": successes / evaluable if evaluable else 0.0,
        "recall_at_5": recall_sum / evaluable if evaluable else 0.0,
    }


def evaluate_retriever(
    records: list[dict],
    retriever: TracedRetriever,
    *,
    split: str,
) -> EvaluationResult:
    """Evaluate Success@5 and standard Recall@5 after retrieval.

    Success@5 is binary: any Gold chunk ID in the final Cross-Encoder Top5.
    Recall@5 is the fraction of Gold chunk IDs found in that Top5, averaged
    across retrieval-evaluable questions. Non-retrieval categories are
    excluded according to the frozen dataset validator contract.
    """
    if split not in VALID_SPLITS:
        raise ValueError(f"split must be one of {sorted(VALID_SPLITS)}")

    split_records = [record for record in records if record.get("split") == split]
    samples: list[EvaluationSample] = []
    excluded = 0

    for line_number, record in enumerate(records, start=1):
        if record.get("split") != split:
            continue
        if record.get("category") in NON_RETRIEVAL_CATEGORIES:
            excluded += 1
            continue

        question = record["question"]
        # The retriever receives only the frozen original question. Gold IDs
        # are intentionally read only after it has produced all candidates.
        trace = retriever.retrieve_with_trace(question, bm25_query_text=None)
        bm25_ids, dense_ids, rrf_ids, top5_ids = _candidate_ids(trace)
        gold_ids = list(record["gold_chunk_ids"])
        overlap = len(set(top5_ids) & set(gold_ids))
        samples.append(
            EvaluationSample(
                line_number=line_number,
                question=question,
                gold_chunk_ids=gold_ids,
                bm25_top_chunk_ids=bm25_ids,
                dense_top_chunk_ids=dense_ids,
                rrf_top_chunk_ids=rrf_ids,
                retrieved_top5_chunk_ids=top5_ids,
                success_at_5=bool(overlap),
                recall_at_5=overlap / len(gold_ids),
            )
        )

    successes, misses, success_at_5, recall_at_5 = _metrics(samples)
    return EvaluationResult(
        split=split,
        total_records=len(split_records),
        retrieval_evaluable_records=len(samples),
        excluded_non_retrieval_records=excluded,
        successes_at_5=successes,
        misses_at_5=misses,
        success_at_5=success_at_5,
        recall_at_5=recall_at_5,
        samples=samples,
    )
