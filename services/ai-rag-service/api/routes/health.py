"""
Health Check Routes
"""

from fastapi import APIRouter, Response
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for container orchestration
    """
    return {
        "status": "healthy",
        "service": "ai-rag-service",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available
    """
    try:
        # TODO: Add checks for Ollama, Qdrant, etc.
        return {
            "status": "ready",
            "service": "ai-rag-service",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return Response(
            content=f"Service not ready: {str(e)}",
            status_code=503
        )
