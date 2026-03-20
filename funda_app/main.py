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
        raw_body_text: str | None = None
        if request.url.path == "/webhooks/keyai/users":
            raw_body = await request.body()
            raw_body_text = raw_body.decode("utf-8", errors="replace")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "body": raw_body_text,
                },
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        if raw_body_text is not None and response.status_code >= 400:
            logger.warning(
                "Webhook request failed validation",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "body": raw_body_text,
                },
            )
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    app.middleware("http")(log_requests)


app = create_app()
