"""
Health check routes.
"""

from fastapi import APIRouter
from datetime import datetime
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Health status information
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Returns:
        dict: Readiness status
    """
    # Check if all dependencies are ready
    # For now, just return ready
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
