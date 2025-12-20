"""
LLM Settings Schemas for API validation.

Source: Design Document 04_validation_engine_comprehensive_design.md
Verified: 2025-12-19
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    AZURE = "azure"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"


class LLMTaskType(str, Enum):
    """Task types that can have separate LLM configurations."""

    EXTRACTION = "extraction"
    VALIDATION = "validation"
    NECESSITY = "necessity"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    FRAUD_REVIEW = "fraud_review"


class LLMSettingsBase(BaseModel):
    """Base schema for LLM settings."""

    task_type: LLMTaskType = Field(..., description="Task type for this configuration")
    provider: LLMProvider = Field(..., description="LLM provider")
    model_name: str = Field(..., max_length=100, description="Model name/identifier")
    api_endpoint: Optional[str] = Field(None, max_length=500, description="Custom API endpoint")
    temperature: float = Field(0.1, ge=0.0, le=2.0, description="Model temperature")
    max_tokens: int = Field(4096, ge=1, le=128000, description="Maximum tokens")
    fallback_provider: Optional[LLMProvider] = Field(None, description="Fallback provider")
    fallback_model: Optional[str] = Field(None, max_length=100, description="Fallback model")
    rate_limit_rpm: int = Field(60, ge=1, le=10000, description="Rate limit (req/min)")
    rate_limit_tpm: Optional[int] = Field(None, ge=1, description="Rate limit (tokens/min)")
    is_active: bool = Field(True, description="Whether configuration is active")


class LLMSettingsCreate(LLMSettingsBase):
    """Schema for creating LLM settings."""

    pass


class LLMSettingsUpdate(BaseModel):
    """Schema for updating LLM settings (all fields optional)."""

    provider: Optional[LLMProvider] = None
    model_name: Optional[str] = Field(None, max_length=100)
    api_endpoint: Optional[str] = Field(None, max_length=500)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    fallback_provider: Optional[LLMProvider] = None
    fallback_model: Optional[str] = Field(None, max_length=100)
    rate_limit_rpm: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_tpm: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class LLMSettingsResponse(LLMSettingsBase):
    """Schema for LLM settings response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMProviderInfo(BaseModel):
    """Information about an LLM provider."""

    provider: LLMProvider
    display_name: str
    models: list[str]
    requires_api_key: bool
    requires_endpoint: bool
    description: str


class LLMProvidersResponse(BaseModel):
    """Response containing available LLM providers."""

    providers: list[LLMProviderInfo]


class LLMUsageStats(BaseModel):
    """Usage statistics for LLM requests."""

    task_type: str
    provider: str
    model_name: str
    total_requests: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    avg_latency_ms: float
    success_rate: float
    estimated_cost_usd: float
    period_start: datetime
    period_end: datetime


class LLMUsageResponse(BaseModel):
    """Response containing LLM usage statistics."""

    stats: list[LLMUsageStats]
    total_cost_usd: float
    total_tokens: int
    period_start: datetime
    period_end: datetime


class LLMTestRequest(BaseModel):
    """Request to test an LLM provider connection."""

    provider: LLMProvider
    model_name: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None  # Optional for testing before saving


class LLMTestResponse(BaseModel):
    """Response from LLM provider connection test."""

    success: bool
    message: str
    latency_ms: Optional[int] = None
    model_info: Optional[dict] = None
    error: Optional[str] = None


# Provider model mappings
PROVIDER_MODELS = {
    LLMProvider.AZURE: [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-35-turbo",
    ],
    LLMProvider.OPENAI: [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini",
    ],
    LLMProvider.ANTHROPIC: [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
    LLMProvider.OLLAMA: [
        "llama3.3",
        "llama3.2",
        "llama3.1",
        "qwen2.5",
        "qwen2.5-coder",
        "mistral",
        "mixtral",
        "phi3",
        "gemma2",
    ],
    LLMProvider.VLLM: [
        "meta-llama/Llama-3.1-8B-Instruct",
        "meta-llama/Llama-3.1-70B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Qwen/Qwen2.5-7B-Instruct",
    ],
}

PROVIDER_INFO = [
    LLMProviderInfo(
        provider=LLMProvider.AZURE,
        display_name="Azure OpenAI",
        models=PROVIDER_MODELS[LLMProvider.AZURE],
        requires_api_key=True,
        requires_endpoint=True,
        description="Microsoft Azure's OpenAI Service with enterprise features",
    ),
    LLMProviderInfo(
        provider=LLMProvider.OPENAI,
        display_name="OpenAI",
        models=PROVIDER_MODELS[LLMProvider.OPENAI],
        requires_api_key=True,
        requires_endpoint=False,
        description="OpenAI's direct API with latest models",
    ),
    LLMProviderInfo(
        provider=LLMProvider.ANTHROPIC,
        display_name="Anthropic Claude",
        models=PROVIDER_MODELS[LLMProvider.ANTHROPIC],
        requires_api_key=True,
        requires_endpoint=False,
        description="Anthropic's Claude models with strong reasoning",
    ),
    LLMProviderInfo(
        provider=LLMProvider.OLLAMA,
        display_name="Ollama (Local)",
        models=PROVIDER_MODELS[LLMProvider.OLLAMA],
        requires_api_key=False,
        requires_endpoint=True,
        description="Local LLM deployment with Ollama",
    ),
    LLMProviderInfo(
        provider=LLMProvider.VLLM,
        display_name="vLLM (Self-hosted)",
        models=PROVIDER_MODELS[LLMProvider.VLLM],
        requires_api_key=False,
        requires_endpoint=True,
        description="High-performance self-hosted LLM serving",
    ),
]
