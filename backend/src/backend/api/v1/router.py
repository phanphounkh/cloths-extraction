from fastapi import APIRouter
from backend.api.v1.routes import health, images

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(images.router)