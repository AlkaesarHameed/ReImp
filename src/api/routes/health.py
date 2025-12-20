"""
Health Check Routes
Service health monitoring endpoints
Source: https://microservices.io/patterns/observability/health-check-api.html
Verified: 2025-11-14
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import check_db_connection, get_session
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint.

    Evidence: Health check pattern for load balancers and monitoring
    Source: https://docs.docker.com/engine/reference/builder/#healthcheck
    Verified: 2025-11-14
    """
    return {
        "status": "healthy",
        "service": "python-project-starter-api",
    }


@router.get("/health/detailed")
async def detailed_health_check(
    session: AsyncSession = Depends(get_session),  # noqa: ARG001
) -> dict[str, Any]:
    """
    Detailed health check with dependency status.

    Evidence: Comprehensive health checks for production monitoring
    Source: https://microservices.io/patterns/observability/health-check-api.html
    Verified: 2025-11-14
    """
    # Check database connection
    db_healthy = await check_db_connection()

    # TODO: Add more checks (Redis, MinIO, etc.)

    overall_status = "healthy" if db_healthy else "unhealthy"

    return {
        "status": overall_status,
        "service": "python-project-starter-api",
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy",
            # "redis": "healthy",
            # "minio": "healthy",
        },
    }
