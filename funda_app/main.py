from fastapi import FastAPI

from funda_app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Funda App API",
        version="0.1.0",
        description="Webhook endpoints for Key.ai events.",
    )
    app.include_router(api_router)
    return app


app = create_app()
