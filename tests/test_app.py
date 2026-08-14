from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from backend.app.main import app, health


def test_application_shell_is_initialized() -> None:
    assert isinstance(app, FastAPI)
    assert app.title == "Fashion Care RAG"
    assert "/" in {route.path for route in app.routes}
    assert "/docs" in {route.path for route in app.routes}
    assert "/api/health" in {route.path for route in app.routes}


class FakeRuntime:
    def check_elasticsearch(self) -> dict[str, str]:
        return {
            "status": "ok",
            "cluster_name": "test-cluster",
            "version": "9.5.1",
            "index_name": "fashion_care_kb_v1",
        }


@pytest.mark.anyio
async def test_health_reports_elasticsearch_status() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime=FakeRuntime())))

    body = await health(request)

    assert body["api"] == "ok"
    assert body["elasticsearch"] == "ok"
    assert body["details"]["cluster_name"] == "test-cluster"
    assert body["details"]["version"] == "9.5.1"
