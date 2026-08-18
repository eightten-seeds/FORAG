"""Synthetic unit tests for Stage 14 Final Evaluation Contract Freeze / Preflight.

All tests in this module are strictly synthetic and do NOT load or evaluate
any Golden TEST records or perform real external LLM calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.app.agent.answer_models import FinalResponse, SourceCitation
from backend.app.agent.state import initialize_agent_state
from backend.app.config import Settings
from backend.app.evaluation.final_metrics import build_final_metrics
from backend.app.evaluation.final_pipeline import (
    FinalEvaluationPipeline,
    build_final_evaluation_pipeline,
)
from backend.app.evaluation.models import EvaluationSampleResult
from backend.app.evaluation.ragchecker_adapter import (
    QwenRAGCheckerLLMAdapter,
    map_evaluation_to_ragchecker_results,
    map_sample_to_ragchecker_result,
    run_ragchecker_evaluation,
)
from backend.app.evaluation.runner import evaluate_final_test
from backend.app.retrieval.models import RetrievalCandidate


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        llm_provider="qwen",
        dashscope_api_key="sk-synthetic-test-key",
        qwen_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        qwen_dev_model="qwen3.7-plus",
        qwen_eval_model="qwen3.7-plus-2026-05-26",
        ragchecker_extractor_model="qwen3.7-plus-2026-05-26",
        ragchecker_checker_model="qwen3.7-plus-2026-05-26",
        llm_enable_thinking=False,
    )


@pytest.fixture
def mock_transport() -> MagicMock:
    transport = MagicMock()
    transport.complete_structured.return_value = "{}"
    return transport


@pytest.fixture
def mock_retriever() -> MagicMock:
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    return retriever


def _make_candidate(chunk_id: str, content: str = "synthetic content") -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        content=content,
        source_id="src_synthetic_1",
        source_title="Source Title",
        section_title="Section Title",
        source_url="https://example.com/source",
        rerank_score=0.95,
        bm25_score=1.5,
        dense_score=0.88,
        rrf_score=0.03,
    )


# ---------------------------------------------------------------------------
# 1. Evaluation factory uses qwen_eval_model
# ---------------------------------------------------------------------------
def test_evaluation_factory_uses_qwen_eval_model(mock_settings, mock_retriever, mock_transport):
    pipeline = build_final_evaluation_pipeline(
        settings=mock_settings,
        retriever=mock_retriever,
        transport=mock_transport,
    )
    assert isinstance(pipeline, FinalEvaluationPipeline)
    assert pipeline.model == mock_settings.qwen_eval_model
    assert pipeline.analyzer.model == "qwen3.7-plus-2026-05-26"
    assert pipeline.evidence_judge.model == "qwen3.7-plus-2026-05-26"
    assert pipeline.query_rewriter.model == "qwen3.7-plus-2026-05-26"
    assert pipeline.answer_generator.model == "qwen3.7-plus-2026-05-26"


# ---------------------------------------------------------------------------
# 2. Normal application still uses qwen_dev_model
# ---------------------------------------------------------------------------
def test_normal_application_uses_qwen_dev_model(mock_settings, monkeypatch):
    from backend.app.agent.answer_generator import AnswerGenerator
    from backend.app.agent.evidence_judge import EvidenceJudge
    from backend.app.agent.query_rewriter import QueryRewriter
    from backend.app.query_analysis.analyzer import QueryAnalyzer

    monkeypatch.setattr(
        "backend.app.llm.client.QwenOpenAICompatibleClient.from_settings",
        lambda s: MagicMock(),
    )

    analyzer = QueryAnalyzer.from_settings(mock_settings)
    judge = EvidenceJudge.from_settings(mock_settings)
    rewriter = QueryRewriter.from_settings(mock_settings)
    generator = AnswerGenerator.from_settings(mock_settings)

    assert analyzer.model == mock_settings.qwen_dev_model == "qwen3.7-plus"
    assert judge.model == mock_settings.qwen_dev_model == "qwen3.7-plus"
    assert rewriter.model == mock_settings.qwen_dev_model == "qwen3.7-plus"
    assert generator.model == mock_settings.qwen_dev_model == "qwen3.7-plus"


# ---------------------------------------------------------------------------
# 3. Extractor uses fixed evaluator snapshot
# ---------------------------------------------------------------------------
def test_extractor_uses_fixed_evaluator_snapshot(mock_settings):
    assert mock_settings.ragchecker_extractor_model == "qwen3.7-plus-2026-05-26"


# ---------------------------------------------------------------------------
# 4. Checker uses fixed evaluator snapshot
# ---------------------------------------------------------------------------
def test_checker_uses_fixed_evaluator_snapshot(mock_settings):
    assert mock_settings.ragchecker_checker_model == "qwen3.7-plus-2026-05-26"


# ---------------------------------------------------------------------------
# 5. Only question enters Final Pipeline
# ---------------------------------------------------------------------------
def test_only_question_enters_final_pipeline(mock_settings):
    invoked_inputs: list[dict[str, Any]] = []

    mock_graph = MagicMock()

    def mock_invoke(state):
        invoked_inputs.append(dict(state))
        return {
            "final_response": FinalResponse(
                status="answered",
                answer="Synthetic answered text.",
                sources=[
                    SourceCitation(
                        evidence_id="E1",
                        chunk_id="chunk_test_1",
                        source_title="Title",
                        section_title="Sec",
                        source_url="https://url.com",
                    )
                ],
            ),
            "retrieval_evidence": (_make_candidate("chunk_test_1"),),
            "rewrite_count": 0,
            "retrieval_pass_count": 1,
        }

    mock_graph.invoke = mock_invoke
    pipeline = FinalEvaluationPipeline(
        graph=mock_graph,
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [
        {
            "evaluation_id": "test_001",
            "question": "How to wash synthetic garment?",
            "gt_answer": "Secret gold answer text",
            "gold_chunk_ids": ["chunk_test_1"],
            "category": "hardshell_washing",
            "split": "test",
        }
    ]

    exec_result, rag_results = evaluate_final_test(
        records,
        pipeline=pipeline,
        settings=mock_settings,
        split="test",
    )

    assert len(invoked_inputs) == 1
    input_state = invoked_inputs[0]
    assert input_state["original_query"] == "How to wash synthetic garment?"
    assert "gt_answer" not in input_state
    assert "gold_chunk_ids" not in input_state
    assert "category" not in input_state


# ---------------------------------------------------------------------------
# 6. Gold / gt_answer unavailable before FinalResponse
# ---------------------------------------------------------------------------
def test_gold_annotations_unavailable_before_final_response(mock_settings):
    state_at_invocation = None

    class SpyGraph:
        def invoke(self, state):
            nonlocal state_at_invocation
            state_at_invocation = dict(state)
            assert "gold_chunk_ids" not in state
            assert "gt_answer" not in state
            return {
                "final_response": FinalResponse(
                    status="answered",
                    answer="Synthetic answer",
                    sources=[
                        SourceCitation(
                            evidence_id="E1",
                            chunk_id="c1",
                            source_title="T",
                            section_title="S",
                            source_url="U",
                        )
                    ],
                ),
                "retrieval_evidence": (_make_candidate("c1"),),
            }

    pipeline = FinalEvaluationPipeline(
        graph=SpyGraph(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [
        {
            "question": "Sample question?",
            "gt_answer": "GT Answer",
            "gold_chunk_ids": ["c1"],
            "category": "care",
            "split": "test",
        }
    ]

    exec_result, _ = evaluate_final_test(
        records,
        pipeline=pipeline,
        settings=mock_settings,
        split="test",
    )
    assert exec_result.success_at_5 == 1.0
    assert exec_result.recall_at_5 == 1.0


# ---------------------------------------------------------------------------
# 7. Final Evidence used for Recall@5
# ---------------------------------------------------------------------------
def test_final_evidence_used_for_recall_at_5(mock_settings):
    class MockGraph:
        def invoke(self, state):
            return {
                "final_response": FinalResponse(
                    status="answered",
                    answer="Answer",
                    sources=[
                        SourceCitation(
                            evidence_id="E1",
                            chunk_id="chunk_a",
                            source_title="T",
                            section_title="S",
                            source_url="U",
                        )
                    ],
                ),
                "retrieval_evidence": (
                    _make_candidate("chunk_a"),
                    _make_candidate("chunk_b"),
                    _make_candidate("chunk_c"),
                    _make_candidate("chunk_d"),
                    _make_candidate("chunk_e"),
                    _make_candidate("chunk_f"),  # 6th candidate: excluded from Top5
                ),
            }

    pipeline = FinalEvaluationPipeline(
        graph=MockGraph(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [
        {
            "question": "Q1",
            "gt_answer": "GT1",
            "gold_chunk_ids": ["chunk_a", "chunk_b"],
            "category": "care",
            "split": "test",
        },
        {
            "question": "Q2",
            "gt_answer": "GT2",
            "gold_chunk_ids": ["chunk_f"],  # In evidence but at index 5 (6th position)
            "category": "care",
            "split": "test",
        },
    ]

    exec_result, _ = evaluate_final_test(
        records,
        pipeline=pipeline,
        settings=mock_settings,
        split="test",
    )

    assert exec_result.samples[0].success_at_5 is True
    assert exec_result.samples[0].recall_at_5 == 1.0
    assert exec_result.samples[1].success_at_5 is False
    assert exec_result.samples[1].recall_at_5 == 0.0
    assert exec_result.successes_at_5 == 1
    assert exec_result.misses_at_5 == 1
    assert exec_result.success_at_5 == 0.5
    assert exec_result.recall_at_5 == 0.5


# ---------------------------------------------------------------------------
# 8. Rewrite scenario uses second-pass Evidence as final Evidence
# ---------------------------------------------------------------------------
def test_rewrite_scenario_uses_second_pass_evidence(mock_settings):
    class RewriteMockGraph:
        def invoke(self, state):
            return {
                "final_response": FinalResponse(
                    status="answered",
                    answer="Answer after rewrite",
                    sources=[
                        SourceCitation(
                            evidence_id="E1",
                            chunk_id="chunk_pass2_1",
                            source_title="T",
                            section_title="S",
                            source_url="U",
                        )
                    ],
                ),
                "retrieval_evidence": (
                    _make_candidate("chunk_pass2_1"),
                    _make_candidate("chunk_pass2_2"),
                ),
                "retrieval_pass_count": 2,
                "rewrite_count": 1,
            }

    pipeline = FinalEvaluationPipeline(
        graph=RewriteMockGraph(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [
        {
            "question": "Vague question requiring rewrite",
            "gt_answer": "GT Answer",
            "gold_chunk_ids": ["chunk_pass2_1"],
            "category": "care",
            "split": "test",
        }
    ]

    exec_result, _ = evaluate_final_test(
        records,
        pipeline=pipeline,
        settings=mock_settings,
        split="test",
    )

    sample = exec_result.samples[0]
    assert sample.rewrite_count == 1
    assert sample.retrieval_pass_count == 2
    assert sample.final_top5_chunk_ids == ["chunk_pass2_1", "chunk_pass2_2"]
    assert sample.success_at_5 is True
    assert sample.recall_at_5 == 1.0


# ---------------------------------------------------------------------------
# 9. RAGChecker input mapping
# ---------------------------------------------------------------------------
def test_ragchecker_input_mapping():
    sample = EvaluationSampleResult(
        evaluation_id="test_042",
        line_number=42,
        question="How do I wash down jacket?",
        split="test",
        category="down_washing",
        gold_chunk_ids=["chunk_down_1"],
        gt_answer="Wash with mild detergent on gentle cycle.",
        final_response_status="answered",
        generated_response="Use mild down cleaner.",
        final_top5_chunk_ids=["chunk_down_1"],
        retrieved_context=[{"doc_id": "chunk_down_1", "text": "Down care instructions."}],
        rewrite_count=0,
        retrieval_pass_count=1,
        success_at_5=True,
        recall_at_5=1.0,
        is_retrieval_evaluable=True,
    )

    rag_result = map_sample_to_ragchecker_result(sample)
    assert rag_result.query_id == "test_042"
    assert rag_result.query == "How do I wash down jacket?"
    assert rag_result.gt_answer == "Wash with mild detergent on gentle cycle."
    assert rag_result.response == "Use mild down cleaner."
    assert len(rag_result.retrieved_context) == 1
    assert rag_result.retrieved_context[0].doc_id == "chunk_down_1"
    assert rag_result.retrieved_context[0].text == "Down care instructions."

    rag_results = map_evaluation_to_ragchecker_results([sample])
    assert len(rag_results.results) == 1
    assert rag_results.results[0].query_id == "test_042"


# ---------------------------------------------------------------------------
# 10. Terminal responses retained without modification
# ---------------------------------------------------------------------------
def test_terminal_responses_retained(mock_settings):
    class TerminalMockGraph:
        def invoke(self, state):
            return {
                "final_response": FinalResponse(
                    status="insufficient_evidence",
                    answer="I cannot answer because evidence is insufficient.",
                    sources=[],
                ),
                "retrieval_evidence": (_make_candidate("chunk_unrelated"),),
                "rewrite_count": 1,
                "retrieval_pass_count": 2,
            }

    pipeline = FinalEvaluationPipeline(
        graph=TerminalMockGraph(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [
        {
            "question": "Obscure care question",
            "gt_answer": "GT Answer",
            "gold_chunk_ids": ["chunk_target"],
            "category": "rare_issue",
            "split": "test",
        }
    ]

    exec_result, rag_results = evaluate_final_test(
        records,
        pipeline=pipeline,
        settings=mock_settings,
        split="test",
    )

    sample = exec_result.samples[0]
    assert sample.final_response_status == "insufficient_evidence"
    assert sample.generated_response == "I cannot answer because evidence is insufficient."
    assert rag_results.results[0].response == "I cannot answer because evidence is insufficient."


# ---------------------------------------------------------------------------
# 11. No sample dropping
# ---------------------------------------------------------------------------
def test_no_sample_dropping(mock_settings):
    class MixedMockGraph:
        def invoke(self, state):
            q = state["original_query"]
            if "answered" in q:
                return {
                    "final_response": FinalResponse(
                        status="answered",
                        answer="Answered text",
                        sources=[
                            SourceCitation(
                                evidence_id="E1",
                                chunk_id="c1",
                                source_title="T",
                                section_title="S",
                                source_url="U",
                            )
                        ],
                    ),
                    "retrieval_evidence": (_make_candidate("c1"),),
                }
            return {
                "final_response": FinalResponse(
                    status="needs_more_information",
                    answer="Please specify your garment material.",
                    sources=[],
                ),
                "retrieval_evidence": (),
            }

    pipeline = FinalEvaluationPipeline(
        graph=MixedMockGraph(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [
        {"question": "answered 1", "split": "test", "gold_chunk_ids": ["c1"], "category": "care"},
        {"question": "missing 2", "split": "test", "gold_chunk_ids": [], "category": "missing_information"},
        {"question": "answered 3", "split": "test", "gold_chunk_ids": ["c1"], "category": "care"},
        {"question": "insufficient 4", "split": "test", "gold_chunk_ids": [], "category": "insufficient_evidence"},
    ]

    exec_result, rag_results = evaluate_final_test(
        records,
        pipeline=pipeline,
        settings=mock_settings,
        split="test",
    )

    assert exec_result.total_samples == 4
    assert len(exec_result.samples) == 4
    assert len(rag_results.results) == 4
    assert exec_result.retrieval_evaluable_samples == 2
    assert exec_result.excluded_non_retrieval_samples == 2


# ---------------------------------------------------------------------------
# 12. final_metrics serialization
# ---------------------------------------------------------------------------
def test_final_metrics_serialization():
    ragchecker_metrics = {
        "retriever_metrics": {
            "claim_recall": 82.5,
            "context_precision": 78.0,
        },
        "generator_metrics": {
            "faithfulness": 91.2,
        },
    }

    metrics = build_final_metrics(
        system_commit="d386f0720f07aa5f6446f37f939a5b96e7a831da",
        kb_version="kb_v1",
        test_samples=16,
        retrieval_evaluable_samples=15,
        embedding_model="intfloat/multilingual-e5-small",
        reranker_model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        pipeline_llm_model="qwen3.7-plus-2026-05-26",
        ragchecker_extractor_model="qwen3.7-plus-2026-05-26",
        ragchecker_checker_model="qwen3.7-plus-2026-05-26",
        success_at_5=0.8,
        recall_at_5=0.75,
        ragchecker_metrics=ragchecker_metrics,
        official_run_id="official_stage14_run_001",
        timestamp="2026-08-18T12:00:00Z",
    )

    assert metrics["system_commit"] == "d386f0720f07aa5f6446f37f939a5b96e7a831da"
    assert metrics["kb_version"] == "kb_v1"
    assert metrics["test_samples"] == 16
    assert metrics["retrieval_evaluable_samples"] == 15
    assert metrics["success_at_5"] == 0.8
    assert metrics["recall_at_5"] == 0.75
    assert metrics["claim_recall"] == 82.5
    assert metrics["context_precision"] == 78.0
    assert metrics["faithfulness"] == 91.2
    assert metrics["official_run_id"] == "official_stage14_run_001"
    assert metrics["timestamp"] == "2026-08-18T12:00:00Z"


# ---------------------------------------------------------------------------
# 13. results paths ignored in .gitignore
# ---------------------------------------------------------------------------
def test_results_paths_ignored():
    from pathlib import Path
    gitignore = Path("f:/FORAG/.gitignore").read_text(encoding="utf-8")
    assert "results/*" in gitignore


# ---------------------------------------------------------------------------
# 14. Final runner cannot accidentally run DEV as official final TEST
# ---------------------------------------------------------------------------
def test_final_runner_split_validation(mock_settings):
    pipeline = FinalEvaluationPipeline(
        graph=MagicMock(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    with pytest.raises(ValueError, match="split must be one of"):
        evaluate_final_test([], pipeline=pipeline, settings=mock_settings, split="invalid_split")

    dev_records = [{"question": "Q", "split": "dev"}]
    with pytest.raises(ValueError, match="No records found for split='test'"):
        evaluate_final_test(dev_records, pipeline=pipeline, settings=mock_settings, split="test")


# ---------------------------------------------------------------------------
# 15. Official run metadata present
# ---------------------------------------------------------------------------
def test_official_run_metadata(mock_settings):
    class SimpleGraph:
        def invoke(self, state):
            return {
                "final_response": FinalResponse(
                    status="answered",
                    answer="Ans",
                    sources=[
                        SourceCitation(
                            evidence_id="E1",
                            chunk_id="c1",
                            source_title="T",
                            section_title="S",
                            source_url="U",
                        )
                    ],
                ),
                "retrieval_evidence": (_make_candidate("c1"),),
            }

    pipeline = FinalEvaluationPipeline(
        graph=SimpleGraph(),
        transport=MagicMock(),
        analyzer=MagicMock(),
        evidence_judge=MagicMock(),
        query_rewriter=MagicMock(),
        answer_generator=MagicMock(),
        model=mock_settings.qwen_eval_model,
    )

    records = [{"question": "Q", "split": "test", "gold_chunk_ids": ["c1"], "category": "care", "kb_version": "kb_v1"}]
    exec_result, _ = evaluate_final_test(records, pipeline=pipeline, settings=mock_settings, split="test", system_commit="d386f072")

    assert exec_result.split == "test"
    assert exec_result.system_commit == "d386f072"
    assert exec_result.kb_version == "kb_v1"
    assert exec_result.pipeline_llm_model == mock_settings.qwen_eval_model
    assert exec_result.embedding_model == mock_settings.embedding_model
    assert exec_result.reranker_model == mock_settings.reranker_model


# ---------------------------------------------------------------------------
# 16. RAGChecker Adapter Smoke Test (mock LLM)
# ---------------------------------------------------------------------------
def test_ragchecker_adapter_synthetic_smoke(mock_settings):
    sample = EvaluationSampleResult(
        evaluation_id="smoke_001",
        line_number=1,
        question="How to clean jacket?",
        split="test",
        category="care",
        gold_chunk_ids=["c1"],
        gt_answer="Clean gently.",
        final_response_status="answered",
        generated_response="Clean gently with water.",
        final_top5_chunk_ids=["c1"],
        retrieved_context=[{"doc_id": "c1", "text": "Clean gently with cold water."}],
        rewrite_count=0,
        retrieval_pass_count=1,
        success_at_5=True,
        recall_at_5=1.0,
        is_retrieval_evaluable=True,
    )
    rag_results = map_evaluation_to_ragchecker_results([sample])

    mock_checker = MagicMock()
    mock_checker.evaluate.return_value = {
        "retriever_metrics": {"claim_recall": 100.0, "context_precision": 100.0},
        "generator_metrics": {"faithfulness": 100.0},
    }

    metrics = run_ragchecker_evaluation(
        rag_results,
        mock_settings,
        custom_checker=mock_checker,
    )
    assert metrics["retriever_metrics"]["claim_recall"] == 100.0
    assert metrics["generator_metrics"]["faithfulness"] == 100.0
