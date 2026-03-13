from fastapi import APIRouter

from funda_app.api.health import router as health_router
from funda_app.api.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(webhooks_router)
