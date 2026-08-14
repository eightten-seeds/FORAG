from fastapi import FastAPI

from backend.app.main import app


def test_application_shell_is_initialized() -> None:
    assert isinstance(app, FastAPI)
    assert app.title == "Fashion Care RAG"
    assert "/" in {route.path for route in app.routes}
    assert "/docs" in {route.path for route in app.routes}
