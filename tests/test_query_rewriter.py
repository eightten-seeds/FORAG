from __future__ import annotations

import json

import pytest

from backend.app.agent.query_rewriter import (
    QueryRewriter,
    QueryRewriteProviderError,
    QueryRewriteValidationError,
)
from backend.app.retrieval.models import RetrievalCandidate


class FakeTransport:
    def __init__(self, content: str | Exception) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def complete_structured(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        if isinstance(self.content, Exception):
            raise self.content
        return self.content


def candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id="chunk-1",
        content="DWR may need reactivation after washing.",
        source_id="source-1",
        source_title="Official care guide",
        source_url="https://example.com/care",
        section_title="Water repellency",
    )


def test_query_rewriter_returns_one_validated_query_without_mutating_original() -> None:
    transport = FakeTransport(json.dumps({"reformulated_query": "  DWR reactivation after washing  "}))
    rewriter = QueryRewriter(transport, model="qwen3.7-plus")
    original = "Why does my jacket stop beading water?"

    result = rewriter.rewrite(original, [candidate()])

    assert result.reformulated_query == "DWR reactivation after washing"
    assert original == "Why does my jacket stop beading water?"
    request = transport.calls[0]
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert request["enable_thinking"] is False
    assert request["messages"][1]["content"].startswith("Original user question:\n" + original)
    assert "gold" not in request["messages"][1]["content"].lower()


@pytest.mark.parametrize("value", ["", "   "])
def test_query_rewriter_rejects_blank_provider_output(value: str) -> None:
    rewriter = QueryRewriter(
        FakeTransport(json.dumps({"reformulated_query": value})),
        model="qwen3.7-plus",
    )

    with pytest.raises(QueryRewriteValidationError, match="schema validation"):
        rewriter.rewrite("question", [candidate()])


def test_query_rewriter_normalizes_provider_error() -> None:
    rewriter = QueryRewriter(FakeTransport(RuntimeError("network down")), model="qwen3.7-plus")

    with pytest.raises(QueryRewriteProviderError, match="request failed"):
        rewriter.rewrite("question", [candidate()])
