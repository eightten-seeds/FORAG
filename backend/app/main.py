"""Stage 11A FastAPI integration for the compiled RAG Agent graph."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.schemas import ChatRequest, ChatResponse, HealthResponse, MetricsResponse
from backend.app.config import Settings, get_settings
from backend.app.logging_config import configure_logging
from backend.app.observability import request_timing, time_stage
from backend.app.runtime import AppRuntime, create_runtime
from backend.app.services.rag_service import RAGServiceError


RuntimeFactory = Callable[[Settings], AppRuntime]
logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    runtime_factory: RuntimeFactory = create_runtime,
) -> FastAPI:
    """Create an injectable app whose heavyweight runtime starts only in lifespan."""

    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
        logger.info("Application starting", extra={"environment": app_settings.app_env})
        with time_stage("runtime_initialization"):
            runtime = runtime_factory(app_settings)
        app_instance.state.runtime = runtime
        try:
            yield
        finally:
            runtime.close()
            logger.info("Application stopped")

    app = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        description="Stage 11A backend integration for the grounded RAG Agent.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    def runtime_or_503(request: Request) -> AppRuntime:
        runtime: AppRuntime | None = getattr(request.app.state, "runtime", None)
        if runtime is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "runtime_unavailable", "message": "Application runtime is unavailable."},
            )
        return runtime

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {"name": app_settings.app_name, "status": "ok", "stage": "stage-11a-backend"}

    @app.get("/api/health", response_model=HealthResponse, tags=["system"])
    def health(request: Request) -> HealthResponse:
        runtime = runtime_or_503(request)
        try:
            es_status = runtime.check_elasticsearch()
        except Exception:
            logger.exception("Elasticsearch health check failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "elasticsearch_unavailable", "message": "Elasticsearch is unavailable."},
            ) from None
        return HealthResponse(
            api="ok",
            runtime="initialized",
            elasticsearch="ok",
            details={
                "cluster_name": es_status["cluster_name"],
                "version": es_status["version"],
                "index_name": app_settings.es_index_name,
            },
        )

    @app.get("/api/metrics", response_model=MetricsResponse, tags=["system"])
    def metrics() -> MetricsResponse:
        return MetricsResponse(
            available=False,
            metrics=None,
            reason="Final full-system evaluation has not been run.",
        )

    @app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
    def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        with request_timing() as timing:
            try:
                runtime = runtime_or_503(request)
                result = runtime.rag_service.chat(payload.question)
                with time_stage("api_projection"):
                    response = ChatResponse.model_validate(result.model_dump())
                return response
            except RAGServiceError:
                logger.exception("RAG service contract failure")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": "rag_unavailable", "message": "The answer service is unavailable."},
                ) from None
            except Exception:
                logger.exception("RAG workflow execution failed")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"code": "workflow_failed", "message": "The answer workflow failed."},
                ) from None
            finally:
                logger.info("RAG request timing: %s", timing.as_safe_dict())

    return app


app = create_app()
