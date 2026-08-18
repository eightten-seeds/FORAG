"""Stage 14 composition of the frozen graph with evaluation-model snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.agent.answer_generator import AnswerGenerator
from backend.app.agent.evidence_judge import EvidenceJudge
from backend.app.agent.graph import FrozenRetriever, build_agent_graph
from backend.app.agent.query_rewriter import QueryRewriter
from backend.app.config import Settings
from backend.app.llm.client import QwenOpenAICompatibleClient, StructuredOutputTransport
from backend.app.query_analysis.analyzer import QueryAnalyzer


@dataclass(frozen=True)
class FinalEvaluationPipeline:
    """Evaluation-only graph and its explicitly pinned business consumers."""

    graph: Any
    transport: StructuredOutputTransport
    analyzer: QueryAnalyzer
    evidence_judge: EvidenceJudge
    query_rewriter: QueryRewriter
    answer_generator: AnswerGenerator
    model: str


def build_final_evaluation_pipeline(
    *,
    settings: Settings,
    retriever: FrozenRetriever,
    transport: StructuredOutputTransport | None = None,
) -> FinalEvaluationPipeline:
    """Compose the frozen graph with `qwen_eval_model`, never the app dev model.

    The production runtime remains responsible for its normal `qwen_dev_model`
    composition. This factory is intentionally evaluation-only.
    """
    evaluation_transport = transport or QwenOpenAICompatibleClient.from_settings(settings)
    model = settings.qwen_eval_model
    analyzer = QueryAnalyzer(
        evaluation_transport,
        model=model,
        enable_thinking=settings.llm_enable_thinking,
    )
    evidence_judge = EvidenceJudge(
        evaluation_transport,
        model=model,
        enable_thinking=settings.llm_enable_thinking,
    )
    query_rewriter = QueryRewriter(
        evaluation_transport,
        model=model,
        enable_thinking=settings.llm_enable_thinking,
    )
    answer_generator = AnswerGenerator(
        evaluation_transport,
        model=model,
        enable_thinking=settings.llm_enable_thinking,
    )
    return FinalEvaluationPipeline(
        graph=build_agent_graph(
            analyzer=analyzer,
            retriever=retriever,
            evidence_judge=evidence_judge,
            query_rewriter=query_rewriter,
            answer_generator=answer_generator,
        ),
        transport=evaluation_transport,
        analyzer=analyzer,
        evidence_judge=evidence_judge,
        query_rewriter=query_rewriter,
        answer_generator=answer_generator,
        model=model,
    )
