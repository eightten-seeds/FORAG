from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.agent.answer_models import FinalResponse, SourceCitation
from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services.models import ChatTrace, EvidenceItem, RAGServiceResult
from backend.app.services.rag_service import RAGServiceError


def service_result(status: str = "answered") -> RAGServiceResult:
    sources = (
        [
            SourceCitation(
                evidence_id="E1",
                chunk_id="chunk-1",
                source_title="Official guide",
                section_title="Care",
                source_url="https://example.com/care",
            )
        ]
        if status == "answered"
        else []
    )
    return RAGServiceResult(
        final_response=FinalResponse(
            status=status,  # type: ignore[arg-type]
            answer="Grounded answer [E1]" if status == "answered" else "Please provide more information.",
            sources=sources,
        ),
        evidence=[
            EvidenceItem(
                rank=1,
                chunk_id="chunk-1",
                source_title="Official guide",
                section_title="Care",
                source_url="https://example.com/care",
                content="Evidence content",
            )
        ],
        trace=ChatTrace(
            query_analysis_completed=True,
            retrieval_pass_count=1,
            rewrite_occurred=False,
            rewrite_count=0,
            evidence_grade="sufficient" if status == "answered" else "insufficient",
            insufficient_reason=None if status == "answered" else "missing_information",
            final_route="ready_for_generation" if status == "answered" else "insufficient_evidence",
            final_status=status,
            retrieval_passes=[],
        ),
    )


class FakeService:
    def __init__(self, result: RAGServiceResult | Exception) -> None:
        self.result = result
        self.calls: list[str] = []

    def chat(self, question: str) -> RAGServiceResult:
        self.calls.append(question)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeRuntime:
    def __init__(self, service: FakeService) -> None:
        self.rag_service = service
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1

    def check_elasticsearch(self) -> dict[str, str]:
        return {"status": "ok", "cluster_name": "test-cluster", "version": "9.5.1"}


def build_client(runtime: FakeRuntime) -> TestClient:
    settings = Settings(frontend_url="http://frontend.test")
    return TestClient(create_app(settings=settings, runtime_factory=lambda _: runtime))


def test_lifespan_builds_once_reuses_runtime_and_closes_it() -> None:
    runtime = FakeRuntime(FakeService(service_result()))
    with build_client(runtime) as client:
        assert client.get("/api/health").status_code == 200
        assert client.post("/api/chat", json={"question": "first"}).status_code == 200
        assert client.post("/api/chat", json={"question": "second"}).status_code == 200
        assert runtime.rag_service.calls == ["first", "second"]
    assert runtime.close_calls == 1


@pytest.mark.parametrize("terminal_status", ["answered", "needs_more_information", "insufficient_evidence"])
def test_chat_projects_each_business_terminal_state_as_http_200(terminal_status: str) -> None:
    with build_client(FakeRuntime(FakeService(service_result(terminal_status)))) as client:
        response = client.post("/api/chat", json={"question": "  question  "})

    assert response.status_code == 200
    body = response.json()
    assert body["final_response"]["status"] == terminal_status
    assert body["evidence"][0]["rank"] == 1
    assert body["trace"]["retrieval_pass_count"] == 1
    assert "original_query" not in body
    assert "query_analysis" not in body


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "   "}])
def test_chat_rejects_empty_or_whitespace_question(payload: dict[str, str]) -> None:
    with build_client(FakeRuntime(FakeService(service_result()))) as client:
        response = client.post("/api/chat", json=payload)
    assert response.status_code == 422


def test_chat_maps_execution_errors_without_traceback_leakage() -> None:
    with build_client(FakeRuntime(FakeService(RuntimeError("secret backend failure")))) as client:
        response = client.post("/api/chat", json={"question": "question"})
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "workflow_failed"
    assert "secret backend failure" not in response.text


def test_chat_maps_service_contract_error_to_503() -> None:
    with build_client(FakeRuntime(FakeService(RAGServiceError("missing final response")))) as client:
        response = client.post("/api/chat", json={"question": "question"})
    assert response.status_code == 503


def test_health_metrics_and_configured_cors() -> None:
    with build_client(FakeRuntime(FakeService(service_result()))) as client:
        health = client.get("/api/health")
        metrics = client.get("/api/metrics")
        cors = client.options(
            "/api/chat",
            headers={
                "Origin": "http://frontend.test",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert health.status_code == 200
    assert health.json()["runtime"] == "initialized"
    assert metrics.status_code == 200
    metrics_body = metrics.json()
    assert metrics_body["available"] is True
    assert metrics_body["reason"] is None
    assert metrics_body["metrics"]["recall_at_5"] == 87.5
    assert metrics_body["metrics"]["success_at_5"] == 87.5
    assert metrics_body["metrics"]["claim_recall"] == 77.9
    assert metrics_body["metrics"]["context_precision"] == 41.2
    assert metrics_body["metrics"]["faithfulness"] == 81.4
    assert metrics_body["metrics"]["test_samples"] == 16
    assert metrics_body["metrics"]["metric_unit"] == "percent"
    assert metrics_body["metrics"]["system_commit"] == "52e9a1f676dca923a474124862978eac936d79cf"
    assert metrics_body["metrics"]["official_run_id"] == "stage14_official_attempt2_52e9a1f"
    assert cors.headers["access-control-allow-origin"] == "http://frontend.test"
