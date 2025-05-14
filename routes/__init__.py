from fastapi import APIRouter

from routes.wallet import router as wallet_router
from routes.proposals import router as proposals_router
from routes.base import router as base_router
from routes.tags import router as tags_router
from routes.auth import router as auth_router

# Create main router
router = APIRouter()

# Include all routers
router.include_router(base_router)
router.include_router(wallet_router)
router.include_router(proposals_router)
router.include_router(tags_router)
router.include_router(auth_router)
