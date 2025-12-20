"""
LLM Settings API Routes.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19

Provides CRUD operations for tenant-specific LLM configuration.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_db, get_tenant_id
from src.models.user import User
from src.schemas.llm_settings import (
    LLMProvider,
    LLMProviderInfo,
    LLMProvidersResponse,
    LLMSettingsCreate,
    LLMSettingsResponse,
    LLMSettingsUpdate,
    LLMTaskType,
    LLMTestRequest,
    LLMTestResponse,
    LLMUsageResponse,
    PROVIDER_INFO,
)
from src.services.validation.llm_validation_service import (
    get_llm_validation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/llm-settings",
    tags=["LLM Settings"],
    responses={404: {"description": "Not found"}},
)


@router.get("/providers", response_model=LLMProvidersResponse)
async def list_providers() -> LLMProvidersResponse:
    """
    List all available LLM providers with their configurations.

    Returns information about each provider including:
    - Available models
    - Whether API key is required
    - Whether custom endpoint is required
    """
    return LLMProvidersResponse(providers=PROVIDER_INFO)


@router.get("", response_model=list[LLMSettingsResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> list[LLMSettingsResponse]:
    """
    List all LLM settings for the current tenant.

    Returns configurations for each task type.
    """
    from sqlalchemy import select
    from src.models.llm_settings import LLMSettings

    result = await db.execute(
        select(LLMSettings).where(LLMSettings.tenant_id == tenant_id)
    )
    settings = result.scalars().all()

    return [
        LLMSettingsResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            task_type=LLMTaskType(s.task_type),
            provider=LLMProvider(s.provider),
            model_name=s.model_name,
            api_endpoint=s.api_endpoint,
            temperature=float(s.temperature),
            max_tokens=s.max_tokens,
            fallback_provider=LLMProvider(s.fallback_provider) if s.fallback_provider else None,
            fallback_model=s.fallback_model,
            rate_limit_rpm=s.rate_limit_rpm,
            rate_limit_tpm=s.rate_limit_tpm,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in settings
    ]


@router.get("/{task_type}", response_model=LLMSettingsResponse)
async def get_settings(
    task_type: LLMTaskType,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> LLMSettingsResponse:
    """
    Get LLM settings for a specific task type.
    """
    from sqlalchemy import select
    from src.models.llm_settings import LLMSettings

    result = await db.execute(
        select(LLMSettings).where(
            LLMSettings.tenant_id == tenant_id,
            LLMSettings.task_type == task_type.value,
        )
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM settings not found for task type: {task_type.value}",
        )

    return LLMSettingsResponse(
        id=settings.id,
        tenant_id=settings.tenant_id,
        task_type=LLMTaskType(settings.task_type),
        provider=LLMProvider(settings.provider),
        model_name=settings.model_name,
        api_endpoint=settings.api_endpoint,
        temperature=float(settings.temperature),
        max_tokens=settings.max_tokens,
        fallback_provider=LLMProvider(settings.fallback_provider) if settings.fallback_provider else None,
        fallback_model=settings.fallback_model,
        rate_limit_rpm=settings.rate_limit_rpm,
        rate_limit_tpm=settings.rate_limit_tpm,
        is_active=settings.is_active,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.post("", response_model=LLMSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_settings(
    settings_in: LLMSettingsCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> LLMSettingsResponse:
    """
    Create LLM settings for a task type.

    Each tenant can have one configuration per task type.
    """
    from sqlalchemy import select
    from src.models.llm_settings import LLMSettings

    # Check if settings already exist for this task type
    result = await db.execute(
        select(LLMSettings).where(
            LLMSettings.tenant_id == tenant_id,
            LLMSettings.task_type == settings_in.task_type.value,
        )
    )
    existing = result.scalars().first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"LLM settings already exist for task type: {settings_in.task_type.value}",
        )

    # Create new settings
    settings = LLMSettings(
        tenant_id=tenant_id,
        task_type=settings_in.task_type.value,
        provider=settings_in.provider.value,
        model_name=settings_in.model_name,
        api_endpoint=settings_in.api_endpoint,
        temperature=settings_in.temperature,
        max_tokens=settings_in.max_tokens,
        fallback_provider=settings_in.fallback_provider.value if settings_in.fallback_provider else None,
        fallback_model=settings_in.fallback_model,
        rate_limit_rpm=settings_in.rate_limit_rpm,
        rate_limit_tpm=settings_in.rate_limit_tpm,
        is_active=settings_in.is_active,
    )

    db.add(settings)
    await db.commit()
    await db.refresh(settings)

    logger.info(f"Created LLM settings for tenant {tenant_id}, task {settings_in.task_type.value}")

    return LLMSettingsResponse(
        id=settings.id,
        tenant_id=settings.tenant_id,
        task_type=LLMTaskType(settings.task_type),
        provider=LLMProvider(settings.provider),
        model_name=settings.model_name,
        api_endpoint=settings.api_endpoint,
        temperature=float(settings.temperature),
        max_tokens=settings.max_tokens,
        fallback_provider=LLMProvider(settings.fallback_provider) if settings.fallback_provider else None,
        fallback_model=settings.fallback_model,
        rate_limit_rpm=settings.rate_limit_rpm,
        rate_limit_tpm=settings.rate_limit_tpm,
        is_active=settings.is_active,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.put("/{task_type}", response_model=LLMSettingsResponse)
async def update_settings(
    task_type: LLMTaskType,
    settings_in: LLMSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> LLMSettingsResponse:
    """
    Update LLM settings for a task type.
    """
    from sqlalchemy import select
    from src.models.llm_settings import LLMSettings

    result = await db.execute(
        select(LLMSettings).where(
            LLMSettings.tenant_id == tenant_id,
            LLMSettings.task_type == task_type.value,
        )
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM settings not found for task type: {task_type.value}",
        )

    # Update fields that were provided
    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "provider" and value:
            setattr(settings, field, value.value)
        elif field == "fallback_provider" and value:
            setattr(settings, field, value.value)
        elif value is not None:
            setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    # Invalidate cache
    service = get_llm_validation_service()
    cache_key = f"{tenant_id}:{task_type.value}"
    if cache_key in service._tenant_configs:
        del service._tenant_configs[cache_key]

    logger.info(f"Updated LLM settings for tenant {tenant_id}, task {task_type.value}")

    return LLMSettingsResponse(
        id=settings.id,
        tenant_id=settings.tenant_id,
        task_type=LLMTaskType(settings.task_type),
        provider=LLMProvider(settings.provider),
        model_name=settings.model_name,
        api_endpoint=settings.api_endpoint,
        temperature=float(settings.temperature),
        max_tokens=settings.max_tokens,
        fallback_provider=LLMProvider(settings.fallback_provider) if settings.fallback_provider else None,
        fallback_model=settings.fallback_model,
        rate_limit_rpm=settings.rate_limit_rpm,
        rate_limit_tpm=settings.rate_limit_tpm,
        is_active=settings.is_active,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.delete("/{task_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_settings(
    task_type: LLMTaskType,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete LLM settings for a task type.
    """
    from sqlalchemy import select, delete
    from src.models.llm_settings import LLMSettings

    result = await db.execute(
        select(LLMSettings).where(
            LLMSettings.tenant_id == tenant_id,
            LLMSettings.task_type == task_type.value,
        )
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"LLM settings not found for task type: {task_type.value}",
        )

    await db.delete(settings)
    await db.commit()

    logger.info(f"Deleted LLM settings for tenant {tenant_id}, task {task_type.value}")


@router.post("/test", response_model=LLMTestResponse)
async def test_connection(
    test_request: LLMTestRequest,
    current_user: User = Depends(get_current_user),
) -> LLMTestResponse:
    """
    Test LLM provider connection.

    Tests the provider connection without saving configuration.
    """
    import time
    from src.gateways.llm_gateway import LLMGateway, LLMRequest

    start_time = time.perf_counter()

    try:
        gateway = LLMGateway()
        await gateway.initialize()

        # Create a simple test request
        request = LLMRequest.simple("Say 'Connection successful' if you can hear me.")
        request.max_tokens = 20

        if test_request.model_name:
            request.model_override = test_request.model_name

        result = await gateway.execute(request)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if result.success and result.data:
            return LLMTestResponse(
                success=True,
                message="Connection successful",
                latency_ms=latency_ms,
                model_info={
                    "provider": result.data.provider,
                    "model": result.data.model,
                    "response": result.data.content[:100],
                },
            )
        else:
            return LLMTestResponse(
                success=False,
                message="Connection failed",
                latency_ms=latency_ms,
                error=result.error,
            )

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(f"LLM connection test failed: {e}")
        return LLMTestResponse(
            success=False,
            message="Connection test failed",
            latency_ms=latency_ms,
            error=str(e),
        )


@router.get("/usage/stats", response_model=LLMUsageResponse)
async def get_usage_stats(
    tenant_id: UUID = Depends(get_tenant_id),
    current_user: User = Depends(get_current_user),
) -> LLMUsageResponse:
    """
    Get LLM usage statistics for the tenant.
    """
    from datetime import datetime, timezone, timedelta

    service = get_llm_validation_service()
    stats = await service.get_usage_stats(tenant_id=tenant_id)

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=30)

    return LLMUsageResponse(
        stats=[],  # TODO: Aggregate from database
        total_cost_usd=stats.get("total_cost_usd", 0.0),
        total_tokens=stats.get("total_tokens", 0),
        period_start=period_start,
        period_end=now,
    )
