from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.query_analysis.adapter import to_frozen_retriever_inputs
from backend.app.query_analysis.analyzer import (
    QueryAnalysisConfigurationError,
    QueryAnalysisProviderError,
    QueryAnalysisValidationError,
    QueryAnalyzer,
)
from backend.app.query_analysis.models import (
    QueryAnalysisPayload,
    QueryAnalysisResult,
    StructuredQuery,
    provider_response_format,
)
from backend.app.query_analysis.prompt import QUERY_ANALYSIS_PROMPT_VERSION


def result_for_test(**changes: object) -> QueryAnalysisResult:
    data: dict[str, object] = {
        "original_query": "我的 GORE-TEX 冲锋衣不挂水珠了怎么办？",
        "lexical_terms_en": [" GORE-TEX ", "", "DWR", " water repellency "],
        "structured_query": {
            "brand": "Arc'teryx",
            "garment_type": "hardshell",
            "technology": [" GORE-TEX ", ""],
            "issue_type": "water_repellency_loss",
            "intent": "care_troubleshooting",
            "care_stage": "restore_dwr",
        },
    }
    data.update(changes)
    return QueryAnalysisResult.model_validate(data)


def test_schema_is_strict_and_uses_documented_technology_list() -> None:
    result = result_for_test()

    assert result.structured_query.technology == ["GORE-TEX"]
    assert result.structured_query.care_stage == "restore_dwr"
    with pytest.raises(ValidationError):
        StructuredQuery.model_validate(
            {
                "brand": None,
                "garment_type": None,
                "technology": "GORE-TEX",
                "issue_type": None,
                "intent": None,
            }
        )


def test_provider_response_format_uses_the_typed_strict_json_schema() -> None:
    response_format = provider_response_format()
    schema = response_format["json_schema"]["schema"]
    structured_query_schema = schema["$defs"]["StructuredQuery"]

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "forag_query_analysis"
    assert response_format["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"structured_query", "lexical_terms_en"}
    assert schema["properties"]["lexical_terms_en"]["items"] == {"type": "string"}
    assert structured_query_schema["additionalProperties"] is False
    assert set(structured_query_schema["properties"]) == {
        "brand",
        "garment_type",
        "technology",
        "issue_type",
        "intent",
        "care_stage",
    }
    assert {"type": "null"} in structured_query_schema["properties"]["brand"]["anyOf"]
    assert structured_query_schema["properties"]["technology"]["items"] == {"type": "string"}
    assert {"brand", "garment_type", "technology", "issue_type", "intent"}.issubset(
        structured_query_schema["required"]
    )


def test_adapter_normalizes_lexical_terms_and_maps_only_frozen_inputs() -> None:
    inputs = to_frozen_retriever_inputs(result_for_test())

    assert inputs.bm25_query_text == "GORE-TEX DWR water repellency"
    assert inputs.brand == "Arc'teryx"
    assert inputs.technologies == ("GORE-TEX",)
    assert set(inputs.model_dump()) == {"bm25_query_text", "brand", "technologies"}


def test_empty_lexical_terms_fall_back_to_none() -> None:
    inputs = to_frozen_retriever_inputs(result_for_test(lexical_terms_en=[]))

    assert inputs.bm25_query_text is None


def test_original_query_is_preserved_locally_without_llm_rewrite() -> None:
    question = "  我的衣服怎么洗？  "
    result = result_for_test(original_query=question)

    assert result.original_query == question


def test_unsupported_fields_never_cross_the_frozen_retriever_adapter() -> None:
    result = result_for_test()
    inputs = to_frozen_retriever_inputs(result)

    assert result.structured_query.garment_type == "hardshell"
    assert result.structured_query.issue_type == "water_repellency_loss"
    assert result.structured_query.intent == "care_troubleshooting"
    assert result.structured_query.care_stage == "restore_dwr"
    assert "garment_type" not in inputs.model_dump()
    assert "issue_type" not in inputs.model_dump()
    assert "intent" not in inputs.model_dump()
    assert "care_stage" not in inputs.model_dump()


class FakeStructuredOutputClient:
    def __init__(self, content: str | Exception) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def complete(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        if isinstance(self.content, Exception):
            raise self.content
        return self.content


def provider_payload() -> str:
    return json.dumps(
        {
            "structured_query": {
                "brand": None,
                "garment_type": "hardshell",
                "technology": ["GORE-TEX"],
                "issue_type": "water_repellency_loss",
                "intent": "care_troubleshooting",
            },
            "lexical_terms_en": ["GORE-TEX", "DWR", "water repellency"],
        }
    )


def test_analyzer_validates_mocked_api_response_and_keeps_original_query() -> None:
    client = FakeStructuredOutputClient(provider_payload())
    analyzer = QueryAnalyzer(client=client, model="qwen3.7-plus")

    result = analyzer.analyze("我的 GORE-TEX 冲锋衣不挂水珠了怎么办？")

    assert result.original_query == "我的 GORE-TEX 冲锋衣不挂水珠了怎么办？"
    assert result.lexical_terms_en == ["GORE-TEX", "DWR", "water repellency"]
    response_format = client.calls[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False
    assert client.calls[0]["temperature"] == 0.0
    assert client.calls[0]["enable_thinking"] is False
    assert "Return JSON only" in str(client.calls[0]["system_prompt"])
    assert QUERY_ANALYSIS_PROMPT_VERSION == "stage8a-v1"


def test_analyzer_surfaces_malformed_or_invalid_provider_output() -> None:
    analyzer = QueryAnalyzer(FakeStructuredOutputClient("not-json"), model="qwen3.7-plus")

    with pytest.raises(QueryAnalysisValidationError, match="schema validation"):
        analyzer.analyze("怎么护理？")

    failing = QueryAnalyzer(FakeStructuredOutputClient(RuntimeError("network down")), model="qwen3.7-plus")
    with pytest.raises(QueryAnalysisProviderError, match="request failed"):
        failing.analyze("怎么护理？")


def test_missing_qwen_configuration_is_explicit() -> None:
    with pytest.raises(QueryAnalysisConfigurationError, match="DASHSCOPE_API_KEY"):
        QueryAnalyzer.from_settings(Settings(dashscope_api_key="", qwen_base_url="https://example.test"))


def test_payload_rejects_unknown_provider_fields() -> None:
    with pytest.raises(ValidationError):
        QueryAnalysisPayload.model_validate(
            {
                "structured_query": {
                    "brand": None,
                    "garment_type": None,
                    "technology": [],
                    "issue_type": None,
                    "intent": None,
                    "unknown": "not allowed",
                },
                "lexical_terms_en": [],
            }
        )
