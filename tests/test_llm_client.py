from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app.llm.client import QwenOpenAICompatibleClient
from backend.app.llm.errors import LLMProviderError


class FakeCompletions:
    def __init__(self, content: str | Exception) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if isinstance(self.content, Exception):
            raise self.content
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


class FakeOpenAIClient:
    def __init__(self, content: str | Exception) -> None:
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


def test_shared_transport_forwards_structured_output_request_unchanged() -> None:
    raw_client = FakeOpenAIClient('{"ok": true}')
    transport = QwenOpenAICompatibleClient(raw_client)
    response_format = {"type": "json_schema", "json_schema": {"strict": True}}
    messages = [
        {"role": "system", "content": "consumer-owned prompt"},
        {"role": "user", "content": "consumer-owned input"},
    ]

    assert transport.complete_structured(
        model="qwen3.7-plus",
        messages=messages,
        response_format=response_format,
        temperature=0.0,
        enable_thinking=False,
    ) == '{"ok": true}'
    assert raw_client.completions.calls == [
        {
            "model": "qwen3.7-plus",
            "messages": messages,
            "response_format": response_format,
            "temperature": 0.0,
            "extra_body": {"enable_thinking": False},
        }
    ]


@pytest.mark.parametrize("content", ["", RuntimeError("network down")])
def test_shared_transport_normalizes_provider_failures(content: str | Exception) -> None:
    transport = QwenOpenAICompatibleClient(FakeOpenAIClient(content))

    with pytest.raises(LLMProviderError):
        transport.complete_structured(
            model="qwen3.7-plus",
            messages=[],
            response_format={"type": "json_schema"},
            temperature=0.0,
            enable_thinking=False,
        )
