"""Evaluation-only composition and artifact contracts for Stage 14."""

from backend.app.evaluation.final_metrics import build_final_metrics
from backend.app.evaluation.final_pipeline import (
    FinalEvaluationPipeline,
    build_final_evaluation_pipeline,
)
from backend.app.evaluation.models import (
    EvaluationSampleResult,
    FinalPipelineExecutionResult,
)
from backend.app.evaluation.ragchecker_adapter import (
    QwenRAGCheckerLLMAdapter,
    map_evaluation_to_ragchecker_results,
    map_sample_to_ragchecker_result,
    run_ragchecker_evaluation,
)
from backend.app.evaluation.runner import evaluate_final_test

__all__ = [
    "EvaluationSampleResult",
    "FinalEvaluationPipeline",
    "FinalPipelineExecutionResult",
    "QwenRAGCheckerLLMAdapter",
    "build_final_evaluation_pipeline",
    "build_final_metrics",
    "evaluate_final_test",
    "map_evaluation_to_ragchecker_results",
    "map_sample_to_ragchecker_result",
    "run_ragchecker_evaluation",
]
