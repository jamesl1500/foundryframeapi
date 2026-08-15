# v1 API router aggregation
from fastapi import APIRouter

from api.api.v1.routes import audits, health, leads

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(audits.router)
router.include_router(leads.router)
