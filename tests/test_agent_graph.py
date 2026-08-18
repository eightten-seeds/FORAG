from __future__ import annotations

from dataclasses import dataclass

from backend.app.agent.evidence_models import EvidenceDecision
from backend.app.agent.graph import build_agent_graph
from backend.app.agent.rewrite_models import RewriteResult
from backend.app.agent.state import initialize_agent_state
from backend.app.query_analysis.models import QueryAnalysisResult
from backend.app.retrieval.models import RetrievalCandidate


def candidate(chunk_id: str) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        content=f"evidence {chunk_id}",
        source_id="source",
        source_title="title",
        source_url="https://example.com",
        section_title="section",
    )


class FakeAnalyzer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def analyze(self, question: str) -> QueryAnalysisResult:
        self.calls.append(question)
        return QueryAnalysisResult.model_validate(
            {
                "original_query": question,
                "lexical_terms_en": ["GORE-TEX", "DWR"],
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


class FakeRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def retrieve(self, original_query: str, **kwargs: object) -> list[RetrievalCandidate]:
        self.calls.append({"original_query": original_query, **kwargs})
        return [candidate(f"chunk-{len(self.calls)}")]


class FakeJudge:
    def __init__(self, decisions: list[EvidenceDecision]) -> None:
        self.decisions = decisions
        self.calls: list[dict[str, object]] = []

    def judge(self, original_query: str, evidence: tuple[RetrievalCandidate, ...]) -> EvidenceDecision:
        self.calls.append({"original_query": original_query, "evidence": evidence})
        return self.decisions.pop(0)


@dataclass
class FakeRewriter:
    reformulated_query: str = "DWR reactivation waterproof jacket"

    def __post_init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def rewrite(self, original_query: str, evidence: tuple[RetrievalCandidate, ...]) -> RewriteResult:
        self.calls.append({"original_query": original_query, "evidence": evidence})
        return RewriteResult(reformulated_query=self.reformulated_query)


def decision(sufficient: bool, reason: str | None = None) -> EvidenceDecision:
    return EvidenceDecision(evidence_sufficient=sufficient, insufficient_reason=reason)


def invoke(decisions: list[EvidenceDecision]):
    analyzer = FakeAnalyzer()
    retriever = FakeRetriever()
    judge = FakeJudge(decisions)
    rewriter = FakeRewriter()
    graph = build_agent_graph(
        analyzer=analyzer,
        retriever=retriever,
        evidence_judge=judge,
        query_rewriter=rewriter,
    )
    original = "My jacket no longer beads water."
    result = graph.invoke(initialize_agent_state(original))
    return result, analyzer, retriever, judge, rewriter, original


def test_graph_sufficient_first_pass_reaches_generation_boundary() -> None:
    result, analyzer, retriever, judge, rewriter, original = invoke([decision(True)])

    assert result["route"] == "ready_for_generation"
    assert analyzer.calls == [original]
    assert len(retriever.calls) == 1
    assert len(judge.calls) == 1
    assert rewriter.calls == []


def test_graph_missing_information_never_calls_rewriter() -> None:
    result, analyzer, retriever, judge, rewriter, original = invoke(
        [decision(False, "missing_information")]
    )

    assert result["route"] == "insufficient_evidence"
    assert analyzer.calls == [original]
    assert len(retriever.calls) == 1
    assert len(judge.calls) == 1
    assert rewriter.calls == []


def test_graph_rewrites_once_then_retrieves_with_frozen_second_pass_contract() -> None:
    result, analyzer, retriever, judge, rewriter, original = invoke(
        [decision(False, "retrieval_problem"), decision(True)]
    )

    assert result["route"] == "ready_for_generation"
    assert analyzer.calls == [original]
    assert len(retriever.calls) == 2
    assert len(judge.calls) == 2
    assert len(rewriter.calls) == 1
    assert retriever.calls[0] == {
        "original_query": original,
        "bm25_query_text": "GORE-TEX DWR",
        "brand": "Arc'teryx",
        "technologies": ("GORE-TEX",),
    }
    assert retriever.calls[1] == {
        "original_query": "DWR reactivation waterproof jacket",
        "bm25_query_text": "DWR reactivation waterproof jacket",
        "brand": "Arc'teryx",
        "technologies": ("GORE-TEX",),
    }
    assert result["original_query"] == original
    assert result["reformulated_query"] == "DWR reactivation waterproof jacket"


def test_graph_second_retrieval_problem_stops_without_second_rewrite() -> None:
    result, analyzer, retriever, judge, rewriter, original = invoke(
        [decision(False, "retrieval_problem"), decision(False, "retrieval_problem")]
    )

    assert result["route"] == "insufficient_evidence"
    assert analyzer.calls == [original]
    assert len(retriever.calls) == 2
    assert len(judge.calls) == 2
    assert len(rewriter.calls) == 1


def test_graph_second_missing_information_stops_and_does_not_use_stale_reason() -> None:
    result, analyzer, retriever, judge, rewriter, original = invoke(
        [decision(False, "retrieval_problem"), decision(False, "missing_information")]
    )

    assert result["route"] == "insufficient_evidence"
    assert result["insufficient_reason"] == "missing_information"
    assert analyzer.calls == [original]
    assert len(retriever.calls) == 2
    assert len(judge.calls) == 2
    assert len(rewriter.calls) == 1
