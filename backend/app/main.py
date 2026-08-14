import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, status

from backend.app.config import get_settings
from backend.app.logging_config import configure_logging
from backend.app.runtime import AppRuntime, create_runtime

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    logger.info("Application starting", extra={"environment": settings.app_env})
    runtime = create_runtime(settings)
    app_instance.state.runtime = runtime
    try:
        yield
    finally:
        runtime.close()
        logger.info("Application stopped")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Stage 1 application shell; RAG features are not implemented yet.",
    lifespan=lifespan,
)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "ok",
        "stage": "elasticsearch-local-environment",
    }


@app.get("/api/health", tags=["system"])
async def health(request: Request) -> dict[str, object]:
    runtime: AppRuntime | None = getattr(request.app.state, "runtime", None)
    if runtime is None:
        runtime = create_runtime(settings)
        request.app.state.runtime = runtime

    try:
        es_status = runtime.check_elasticsearch()
    except Exception as exc:
        logger.exception("Elasticsearch health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "api": "ok",
                "elasticsearch": "error",
                "message": str(exc),
            },
        ) from exc

    return {
        "api": "ok",
        "elasticsearch": "ok",
        "details": {
            "cluster_name": es_status["cluster_name"],
            "version": es_status["version"],
            "url": settings.es_url,
            "index_name": settings.es_index_name,
        },
    }
