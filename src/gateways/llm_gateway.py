"""
LLM Gateway with LiteLLM Integration.

Provides unified access to multiple LLM providers:
- Primary: OpenAI GPT-4o (commercial, reliable)
- Fallback: Ollama (local, open-source)

Features:
- Vision capabilities for document understanding
- Medical claim extraction prompts
- Structured output parsing
- Streaming support
"""

import base64
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Union

from src.core.config import get_claims_settings
from src.core.enums import LLMProvider
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayError,
    ProviderUnavailableError,
    ProviderRateLimitError,
)

logger = logging.getLogger(__name__)

# Import LiteLLM with graceful fallback
try:
    import litellm
    from litellm import acompletion, completion

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.warning("LiteLLM not installed. LLM Gateway will operate in mock mode.")


class MessageRole(str, Enum):
    """Role for LLM messages."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ImageContent:
    """Image content for vision models."""

    image_data: bytes
    media_type: str = "image/png"

    def to_base64(self) -> str:
        """Convert image to base64 string."""
        return base64.b64encode(self.image_data).decode("utf-8")

    def to_data_url(self) -> str:
        """Convert to data URL format."""
        return f"data:{self.media_type};base64,{self.to_base64()}"


@dataclass
class LLMMessage:
    """Message for LLM conversation."""

    role: MessageRole
    content: str
    images: list[ImageContent] = field(default_factory=list)

    def to_litellm_format(self) -> dict[str, Any]:
        """Convert to LiteLLM message format."""
        if not self.images:
            return {"role": self.role.value, "content": self.content}

        # Vision message format
        content_parts = []
        content_parts.append({"type": "text", "text": self.content})

        for image in self.images:
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image.to_data_url()},
                }
            )

        return {"role": self.role.value, "content": content_parts}


@dataclass
class LLMRequest:
    """Request for LLM completion."""

    messages: list[LLMMessage]
    model_override: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096
    json_mode: bool = False
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def simple(cls, prompt: str, system_prompt: Optional[str] = None) -> "LLMRequest":
        """Create a simple text-only request."""
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(LLMMessage(role=MessageRole.USER, content=prompt))
        return cls(messages=messages)

    @classmethod
    def with_image(
        cls,
        prompt: str,
        image_data: bytes,
        media_type: str = "image/png",
        system_prompt: Optional[str] = None,
    ) -> "LLMRequest":
        """Create a vision request with an image."""
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(
            LLMMessage(
                role=MessageRole.USER,
                content=prompt,
                images=[ImageContent(image_data=image_data, media_type=media_type)],
            )
        )
        return cls(messages=messages)


@dataclass
class LLMResponse:
    """Response from LLM completion."""

    content: str
    model: str
    provider: str
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    confidence: Optional[float] = None
    raw_response: Optional[dict] = None

    def parse_json(self) -> dict[str, Any]:
        """Parse response content as JSON."""
        try:
            # Handle markdown code blocks
            content = self.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise GatewayError(f"Failed to parse LLM response as JSON: {e}")


class LLMGateway(BaseGateway[LLMRequest, LLMResponse, LLMProvider]):
    """
    LLM Gateway for claims processing.

    Supports vision models for document understanding:
    - OpenAI GPT-4o (primary, commercial)
    - Ollama (fallback, local)
    - Azure OpenAI (alternative)
    """

    # Model mappings for each provider
    PROVIDER_MODELS = {
        LLMProvider.OLLAMA: {
            "default": "ollama/llama3.2",
            "medical": "ollama/llama3.2",
            "vision": "ollama/llama3.2",
        },
        LLMProvider.OPENAI: {
            "default": "gpt-4o",
            "medical": "gpt-4o",
            "vision": "gpt-4o",
        },
        LLMProvider.ANTHROPIC: {
            "default": "claude-3-5-sonnet-20241022",
            "medical": "claude-3-5-sonnet-20241022",
            "vision": "claude-3-5-sonnet-20241022",
        },
        LLMProvider.AZURE_OPENAI: {
            "default": "azure/gpt-4o",
            "medical": "azure/gpt-4o",
            "vision": "azure/gpt-4o",
        },
    }

    def __init__(self, config: Optional[GatewayConfig] = None):
        settings = get_claims_settings()

        if config is None:
            config = GatewayConfig(
                primary_provider=settings.LLM_PRIMARY_PROVIDER.value,
                fallback_provider=(
                    settings.LLM_FALLBACK_PROVIDER.value
                    if settings.LLM_FALLBACK_ON_ERROR
                    else None
                ),
                fallback_on_error=settings.LLM_FALLBACK_ON_ERROR,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
                confidence_threshold=settings.LLM_CONFIDENCE_THRESHOLD,
            )

        super().__init__(config)
        self._settings = settings
        self._provider_configs: dict[LLMProvider, dict] = {}

    @property
    def gateway_name(self) -> str:
        return "LLM"

    async def _initialize_provider(self, provider: LLMProvider) -> None:
        """Initialize LLM provider configuration."""
        settings = self._settings

        if provider == LLMProvider.OLLAMA:
            print(f"[LLM DEBUG] Initializing Ollama: base_url={settings.OLLAMA_BASE_URL}, model={settings.OLLAMA_MODEL}", flush=True)
            logger.info(f"Initializing Ollama: base_url={settings.OLLAMA_BASE_URL}, model={settings.OLLAMA_MODEL}")
            self._provider_configs[provider] = {
                "api_base": settings.OLLAMA_BASE_URL,
                "model": settings.OLLAMA_MODEL,
                "medical_model": settings.OLLAMA_MEDICAL_MODEL,
            }
            if LITELLM_AVAILABLE:
                # Configure LiteLLM for Ollama
                litellm.api_base = settings.OLLAMA_BASE_URL

        elif provider == LLMProvider.OPENAI:
            if settings.OPENAI_API_KEY:
                print(f"[LLM DEBUG] Initializing OpenAI: model={settings.OPENAI_MODEL}, api_key=****{settings.OPENAI_API_KEY[-4:] if len(settings.OPENAI_API_KEY) > 4 else '****'}", flush=True)
                logger.info(f"Initializing OpenAI: model={settings.OPENAI_MODEL}")
                self._provider_configs[provider] = {
                    "api_key": settings.OPENAI_API_KEY,
                    "model": settings.OPENAI_MODEL,
                }
                # Reset api_base to ensure OpenAI uses its default endpoint
                if LITELLM_AVAILABLE:
                    litellm.api_base = None
            else:
                logger.warning("OpenAI API key not configured")
                raise ProviderUnavailableError(
                    "OpenAI API key not configured", provider=provider.value
                )

        elif provider == LLMProvider.ANTHROPIC:
            if settings.ANTHROPIC_API_KEY:
                self._provider_configs[provider] = {
                    "api_key": settings.ANTHROPIC_API_KEY,
                }
            else:
                logger.warning("Anthropic API key not configured")
                raise ProviderUnavailableError(
                    "Anthropic API key not configured", provider=provider.value
                )

        elif provider == LLMProvider.AZURE_OPENAI:
            if settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT:
                self._provider_configs[provider] = {
                    "api_key": settings.AZURE_OPENAI_API_KEY,
                    "api_base": settings.AZURE_OPENAI_ENDPOINT,
                    "api_version": settings.AZURE_OPENAI_API_VERSION,
                }
            else:
                logger.warning("Azure OpenAI not configured")
                raise ProviderUnavailableError(
                    "Azure OpenAI not configured", provider=provider.value
                )

        logger.info(f"LLM provider {provider.value} initialized")

    async def _execute_request(
        self, request: LLMRequest, provider: LLMProvider
    ) -> LLMResponse:
        """Execute LLM request using specified provider."""
        if not LITELLM_AVAILABLE:
            # Mock response for testing without LiteLLM
            return LLMResponse(
                content='{"mock": "response"}',
                model="mock-model",
                provider=provider.value,
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )

        # Determine model to use
        if request.model_override:
            model = request.model_override
        else:
            model_type = "vision" if any(m.images for m in request.messages) else "default"
            model = self.PROVIDER_MODELS.get(provider, {}).get(
                model_type, self.PROVIDER_MODELS[LLMProvider.OPENAI]["default"]
            )

        # Build LiteLLM messages
        messages = [msg.to_litellm_format() for msg in request.messages]

        # Provider-specific configuration
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        # Add JSON mode if requested
        if request.json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # Add provider-specific config
        provider_config = self._provider_configs.get(provider, {})
        if "api_key" in provider_config:
            kwargs["api_key"] = provider_config["api_key"]
        if "api_base" in provider_config:
            kwargs["api_base"] = provider_config["api_base"]

        # For OpenAI, ensure we're not using a custom api_base
        if provider == LLMProvider.OPENAI and "api_base" not in kwargs:
            # Reset global api_base to prevent Ollama URL being used
            if LITELLM_AVAILABLE:
                litellm.api_base = None

        try:
            import time as _time
            _start = _time.time()
            has_images = any(m.images for m in request.messages)
            print(f"[LLM DEBUG] Request: provider={provider.value}, model={model}, api_base={kwargs.get('api_base', 'NOT SET')}, has_images={has_images}", flush=True)
            logger.info(f"LLM request: provider={provider.value}, model={model}, api_base={kwargs.get('api_base', 'NOT SET')}")
            response = await acompletion(**kwargs)
            print(f"[LLM DEBUG] Response received in {_time.time() - _start:.1f}s", flush=True)

            # Extract response content
            choice = response.choices[0]
            content = choice.message.content or ""

            return LLMResponse(
                content=content,
                model=response.model,
                provider=provider.value,
                finish_reason=choice.finish_reason or "stop",
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "429" in error_str:
                raise ProviderRateLimitError(
                    f"Rate limit exceeded: {e}", provider=provider.value
                )
            elif "unauthorized" in error_str or "401" in error_str:
                raise ProviderUnavailableError(
                    f"Authentication failed: {e}", provider=provider.value
                )
            else:
                raise GatewayError(
                    f"LLM request failed: {e}",
                    provider=provider.value,
                    original_error=e,
                )

    async def _health_check(self, provider: LLMProvider) -> bool:
        """Check if LLM provider is healthy."""
        try:
            test_request = LLMRequest.simple("Say 'ok' if you can hear me.")
            test_request.max_tokens = 10
            await self._execute_request(test_request, provider)
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {provider.value}: {e}")
            return False

    def _parse_provider(self, provider_str: str) -> LLMProvider:
        """Parse provider string to LLMProvider enum."""
        return LLMProvider(provider_str)

    # Convenience methods for claims processing

    async def extract_claim_data(
        self,
        document_image: bytes,
        document_type: str = "medical_claim",
        media_type: str = "image/png",
    ) -> dict[str, Any]:
        """Extract structured claim data from a document image."""
        system_prompt = """You are an expert medical claims processor.
Extract structured data from the provided medical document image.
Return a valid JSON object with the extracted fields.
Be precise with dates, amounts, and codes.
If a field is not visible or unclear, set it to null."""

        extraction_prompt = f"""Analyze this {document_type} document and extract:
1. Patient information (name, DOB, member ID)
2. Provider information (name, NPI, address)
3. Service dates and diagnosis codes (ICD-10)
4. Procedure codes (CPT/HCPCS) and charges
5. Any authorization numbers or references

Return the data as a JSON object with these keys:
- patient: {{name, dob, member_id, address}}
- provider: {{name, npi, address, tax_id}}
- claim: {{service_date, admission_date, discharge_date, total_charges}}
- diagnoses: [{{code, description, qualifier}}]
- procedures: [{{code, description, modifier, units, charge}}]
- authorization: {{number, type}}"""

        request = LLMRequest.with_image(
            prompt=extraction_prompt,
            image_data=document_image,
            media_type=media_type,
            system_prompt=system_prompt,
        )
        request.json_mode = True
        request.temperature = 0.1  # Low temperature for accuracy

        result = await self.execute(request)

        if not result.success or not result.data:
            raise GatewayError(f"Failed to extract claim data: {result.error}")

        return result.data.parse_json()

    async def validate_medical_codes(
        self,
        diagnosis_codes: list[str],
        procedure_codes: list[str],
        coding_standard: str = "us",
    ) -> dict[str, Any]:
        """Validate medical codes using LLM knowledge."""
        system_prompt = """You are a certified medical coder with expertise in ICD-10 and CPT/HCPCS codes.
Validate the provided codes and check for:
1. Code validity and format
2. Code-to-code compatibility (diagnosis supports procedure)
3. Potential unbundling issues
4. Medical necessity indicators
Return validation results as JSON."""

        validation_prompt = f"""Validate these medical codes for a {coding_standard.upper()} standard claim:

Diagnosis codes (ICD-10): {', '.join(diagnosis_codes)}
Procedure codes (CPT/HCPCS): {', '.join(procedure_codes)}

Return JSON with:
- valid_diagnoses: [{{code, valid, description, issues}}]
- valid_procedures: [{{code, valid, description, issues}}]
- compatibility_check: {{compatible, issues}}
- medical_necessity: {{score, reasoning}}
- overall_valid: boolean"""

        request = LLMRequest.simple(validation_prompt, system_prompt)
        request.json_mode = True

        result = await self.execute(request)

        if not result.success or not result.data:
            raise GatewayError(f"Failed to validate codes: {result.error}")

        return result.data.parse_json()

    async def assess_fwa_risk(
        self,
        claim_data: dict[str, Any],
        historical_patterns: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Assess fraud, waste, and abuse risk for a claim."""
        system_prompt = """You are a healthcare fraud investigator with expertise in detecting:
- Upcoding and unbundling
- Duplicate billing
- Services not rendered
- Medically unnecessary procedures
- Provider identity issues
Analyze the claim for potential FWA indicators and return a risk assessment."""

        fwa_prompt = f"""Analyze this claim for FWA (Fraud, Waste, Abuse) indicators:

Claim Data:
{json.dumps(claim_data, indent=2, default=str)}

{f'Historical Patterns: {json.dumps(historical_patterns, indent=2)}' if historical_patterns else ''}

Return JSON with:
- risk_score: float (0.0 to 1.0)
- risk_level: "low" | "medium" | "high" | "critical"
- indicators: [{{type, description, severity, confidence}}]
- recommendation: "approve" | "review" | "investigate" | "deny"
- reasoning: string"""

        request = LLMRequest.simple(fwa_prompt, system_prompt)
        request.json_mode = True

        result = await self.execute(request)

        if not result.success or not result.data:
            raise GatewayError(f"Failed to assess FWA risk: {result.error}")

        return result.data.parse_json()


# Singleton instance
_llm_gateway: Optional[LLMGateway] = None


def get_llm_gateway() -> LLMGateway:
    """Get or create the singleton LLM gateway instance."""
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway()
    return _llm_gateway


async def reset_llm_gateway() -> None:
    """Reset the LLM gateway (for testing)."""
    global _llm_gateway
    if _llm_gateway:
        await _llm_gateway.close()
    _llm_gateway = None
