import logging
import time

from fastapi import FastAPI, Request

from funda_app.api.router import api_router
from funda_app.loggy import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Creates the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI app instance.
    """
    app = FastAPI(
        title="Funda App API",
        version="0.1.0",
        description="Webhook endpoints for Key.ai events.",
    )
    _configure_request_logging(app)
    app.include_router(api_router)
    logger.info("Created Funda App API application.")
    return app


def _configure_request_logging(app: FastAPI) -> None:
    """
    Adds request logging middleware to the FastAPI app.

    Args:
        app (FastAPI): Application instance to configure.
    """

    async def log_requests(request: Request, call_next):
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "Request failed: method=%s path=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Request completed: method=%s path=%s status_code=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    app.middleware("http")(log_requests)


app = create_app()
