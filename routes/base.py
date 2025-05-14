from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint, returns API status"""
    return {"status": "active", "message": "Wallet Analysis API is running"}
