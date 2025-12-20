"""
FastAPI Main Application
Entry point for the API server
Source: https://fastapi.tiangolo.com/
Verified: 2025-11-14
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import settings
from src.api.routes import auth, claims, documents, edi, eligibility, fwa, health, lcd_ncd, llm_settings, users, validation
from src.db.connection import close_db_connection
from src.utils.logging import get_logger, setup_logging

# Setup logging
setup_logging(
    level=settings.LOG_LEVEL,
    json_logs=settings.is_production,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]  # noqa: ARG001
    """
    Application lifespan manager.

    Evidence: Lifespan events for startup/shutdown tasks
    Source: https://fastapi.tiangolo.com/advanced/events/
    Verified: 2025-11-14
    """
    # Startup
    logger.info(f"Starting application in {settings.ENVIRONMENT} mode")
    logger.info(f"Debug mode: {settings.DEBUG}")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db_connection()
    logger.info("Database connections closed")


# Initialize FastAPI app
# Evidence: FastAPI configuration best practices
# Source: https://fastapi.tiangolo.com/tutorial/metadata/
# Verified: 2025-11-14
app = FastAPI(
    title="Python Project Starter API",
    description="Production-ready FastAPI starter with PostgreSQL, Redis, MinIO, and MCP",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS middleware
# Evidence: CORS configuration for web applications
# Source: https://fastapi.tiangolo.com/tutorial/cors/
# Verified: 2025-11-14
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(claims.router)
app.include_router(validation.router)
app.include_router(llm_settings.router)
app.include_router(edi.router)
app.include_router(eligibility.router)
app.include_router(lcd_ncd.router)
app.include_router(fwa.router)


@app.get("/")
async def root() -> dict[str, Any]:
    """
    Root endpoint with API information.

    Evidence: Discoverable API pattern
    Source: https://restfulapi.net/
    Verified: 2025-11-14
    """
    return {
        "name": "Python Project Starter API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if not settings.is_production else "disabled",
    }
