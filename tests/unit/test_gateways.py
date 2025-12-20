"""
Unit tests for provider gateways.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.enums import LLMProvider, OCRProvider, ProviderStatus
from src.gateways.base import (
    BaseGateway,
    GatewayConfig,
    GatewayResult,
    GatewayError,
    ProviderHealth,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ProviderRateLimitError,
)
from src.gateways.llm_gateway import (
    LLMGateway,
    LLMRequest,
    LLMResponse,
    LLMMessage,
    MessageRole,
    ImageContent,
)
from src.gateways.ocr_gateway import (
    OCRGateway,
    OCRRequest,
    OCRResponse,
    OCRTextBlock,
    OCRBoundingBox,
    OCRTableData,
    OCRTableCell,
)


class TestGatewayConfig:
    """Tests for GatewayConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GatewayConfig(primary_provider="test")
        assert config.primary_provider == "test"
        assert config.fallback_provider is None
        assert config.fallback_on_error is True
        assert config.timeout_seconds == 30.0
        assert config.retry_attempts == 3
        assert config.confidence_threshold == 0.85

    def test_with_fallback(self):
        """Test configuration with fallback provider."""
        config = GatewayConfig(
            primary_provider="primary",
            fallback_provider="fallback",
            timeout_seconds=60.0,
        )
        assert config.primary_provider == "primary"
        assert config.fallback_provider == "fallback"
        assert config.timeout_seconds == 60.0


class TestGatewayResult:
    """Tests for GatewayResult dataclass."""

    def test_successful_result(self):
        """Test successful result creation."""
        result = GatewayResult(
            success=True,
            data="test data",
            provider_used="test_provider",
            latency_ms=100.5,
        )
        assert result.success is True
        assert result.data == "test data"
        assert result.provider_used == "test_provider"
        assert result.latency_ms == 100.5
        assert result.fallback_used is False

    def test_failed_result(self):
        """Test failed result creation."""
        result = GatewayResult(
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_low_confidence_detection(self):
        """Test low confidence detection."""
        high_conf = GatewayResult(success=True, confidence=0.95)
        low_conf = GatewayResult(success=True, confidence=0.5)
        no_conf = GatewayResult(success=True, confidence=None)

        assert high_conf.is_low_confidence is False
        assert low_conf.is_low_confidence is True
        assert no_conf.is_low_confidence is False


class TestProviderHealth:
    """Tests for ProviderHealth dataclass."""

    def test_default_health(self):
        """Test default health status."""
        health = ProviderHealth()
        assert health.status == ProviderStatus.HEALTHY
        assert health.consecutive_failures == 0
        assert health.is_circuit_open is False

    def test_record_success(self):
        """Test recording successful request."""
        health = ProviderHealth()
        health.consecutive_failures = 3
        health.status = ProviderStatus.DEGRADED

        health.record_success(latency_ms=50.0)

        assert health.consecutive_failures == 0
        assert health.status == ProviderStatus.HEALTHY
        assert health.request_count == 1
        assert health.avg_latency_ms == 50.0

    def test_record_failure(self):
        """Test recording failed request."""
        health = ProviderHealth()

        health.record_failure("error 1", circuit_breaker_threshold=5, timeout_seconds=60)
        assert health.consecutive_failures == 1
        assert health.error_count == 1
        assert health.status == ProviderStatus.HEALTHY

        health.record_failure("error 2", circuit_breaker_threshold=5, timeout_seconds=60)
        health.record_failure("error 3", circuit_breaker_threshold=5, timeout_seconds=60)
        assert health.status == ProviderStatus.DEGRADED

        health.record_failure("error 4", circuit_breaker_threshold=5, timeout_seconds=60)
        health.record_failure("error 5", circuit_breaker_threshold=5, timeout_seconds=60)
        assert health.status == ProviderStatus.UNHEALTHY
        assert health.is_circuit_open is True

    def test_circuit_breaker_timeout(self):
        """Test circuit breaker timeout."""
        health = ProviderHealth()
        health.circuit_open_until = datetime.now(timezone.utc) + timedelta(seconds=60)
        assert health.is_circuit_open is True

        health.circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert health.is_circuit_open is False


class TestGatewayExceptions:
    """Tests for gateway exceptions."""

    def test_gateway_error(self):
        """Test base gateway error."""
        error = GatewayError("Test error", provider="test", original_error=ValueError("orig"))
        assert str(error) == "Test error"
        assert error.provider == "test"
        assert isinstance(error.original_error, ValueError)

    def test_provider_unavailable_error(self):
        """Test provider unavailable error."""
        error = ProviderUnavailableError("Provider down", provider="test")
        assert "Provider down" in str(error)
        assert error.provider == "test"

    def test_provider_timeout_error(self):
        """Test provider timeout error."""
        error = ProviderTimeoutError("Timeout after 30s", provider="test")
        assert "Timeout" in str(error)

    def test_provider_rate_limit_error(self):
        """Test provider rate limit error."""
        error = ProviderRateLimitError("Rate limit exceeded", provider="test")
        assert "Rate limit" in str(error)


class TestLLMMessage:
    """Tests for LLM message classes."""

    def test_simple_message(self):
        """Test simple text message."""
        msg = LLMMessage(role=MessageRole.USER, content="Hello")
        result = msg.to_litellm_format()
        assert result["role"] == "user"
        assert result["content"] == "Hello"

    def test_system_message(self):
        """Test system message."""
        msg = LLMMessage(role=MessageRole.SYSTEM, content="You are helpful")
        result = msg.to_litellm_format()
        assert result["role"] == "system"

    def test_message_with_image(self):
        """Test message with image content."""
        image = ImageContent(image_data=b"fake_image_data", media_type="image/png")
        msg = LLMMessage(
            role=MessageRole.USER,
            content="What's in this image?",
            images=[image],
        )
        result = msg.to_litellm_format()
        assert result["role"] == "user"
        assert isinstance(result["content"], list)
        assert len(result["content"]) == 2
        assert result["content"][0]["type"] == "text"
        assert result["content"][1]["type"] == "image_url"


class TestImageContent:
    """Tests for ImageContent class."""

    def test_to_base64(self):
        """Test base64 encoding."""
        image = ImageContent(image_data=b"test")
        base64_str = image.to_base64()
        assert base64_str == "dGVzdA=="

    def test_to_data_url(self):
        """Test data URL generation."""
        image = ImageContent(image_data=b"test", media_type="image/jpeg")
        data_url = image.to_data_url()
        assert data_url.startswith("data:image/jpeg;base64,")


class TestLLMRequest:
    """Tests for LLMRequest class."""

    def test_simple_request(self):
        """Test simple request creation."""
        request = LLMRequest.simple("Hello", system_prompt="Be helpful")
        assert len(request.messages) == 2
        assert request.messages[0].role == MessageRole.SYSTEM
        assert request.messages[1].role == MessageRole.USER
        assert request.temperature == 0.1

    def test_request_without_system(self):
        """Test request without system prompt."""
        request = LLMRequest.simple("Hello")
        assert len(request.messages) == 1
        assert request.messages[0].role == MessageRole.USER

    def test_vision_request(self):
        """Test vision request creation."""
        request = LLMRequest.with_image(
            prompt="Describe this",
            image_data=b"fake_image",
            media_type="image/png",
        )
        assert len(request.messages) == 1
        assert len(request.messages[0].images) == 1


class TestLLMResponse:
    """Tests for LLMResponse class."""

    def test_parse_json(self):
        """Test JSON parsing from response."""
        response = LLMResponse(
            content='{"key": "value"}',
            model="test-model",
            provider="test",
        )
        result = response.parse_json()
        assert result == {"key": "value"}

    def test_parse_json_with_markdown(self):
        """Test JSON parsing with markdown code block."""
        response = LLMResponse(
            content='```json\n{"key": "value"}\n```',
            model="test-model",
            provider="test",
        )
        result = response.parse_json()
        assert result == {"key": "value"}

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        response = LLMResponse(
            content="not json",
            model="test-model",
            provider="test",
        )
        with pytest.raises(GatewayError):
            response.parse_json()


class TestOCRBoundingBox:
    """Tests for OCR bounding box."""

    def test_to_dict(self):
        """Test bounding box serialization."""
        bbox = OCRBoundingBox(x=10, y=20, width=100, height=50, rotation=5.0)
        result = bbox.to_dict()
        assert result["x"] == 10
        assert result["y"] == 20
        assert result["width"] == 100
        assert result["height"] == 50
        assert result["rotation"] == 5.0


class TestOCRTextBlock:
    """Tests for OCR text block."""

    def test_to_dict(self):
        """Test text block serialization."""
        bbox = OCRBoundingBox(x=0, y=0, width=100, height=20)
        block = OCRTextBlock(
            text="Hello World",
            confidence=0.95,
            bbox=bbox,
            language="en",
        )
        result = block.to_dict()
        assert result["text"] == "Hello World"
        assert result["confidence"] == 0.95
        assert result["language"] == "en"


class TestOCRTableData:
    """Tests for OCR table data."""

    def test_to_dataframe_dict(self):
        """Test table conversion to dataframe dict."""
        cells = [
            OCRTableCell(text="Name", row=0, column=0),
            OCRTableCell(text="Age", row=0, column=1),
            OCRTableCell(text="John", row=1, column=0),
            OCRTableCell(text="30", row=1, column=1),
            OCRTableCell(text="Jane", row=2, column=0),
            OCRTableCell(text="25", row=2, column=1),
        ]
        table = OCRTableData(cells=cells, row_count=3, column_count=2)
        result = table.to_dataframe_dict()

        assert "Name" in result
        assert "Age" in result
        assert result["Name"] == ["John", "Jane"]
        assert result["Age"] == ["30", "25"]


class TestOCRRequest:
    """Tests for OCR request."""

    def test_default_request(self):
        """Test default request creation."""
        request = OCRRequest(image_data=b"fake_image")
        assert request.languages == ["en"]
        assert request.detect_tables is True
        assert request.dpi == 300

    def test_multilingual_request(self):
        """Test multilingual request."""
        request = OCRRequest(
            image_data=b"fake_image",
            languages=["en", "ar"],
        )
        assert "ar" in request.languages


class TestOCRResponse:
    """Tests for OCR response."""

    def test_full_text_property(self):
        """Test full text extraction."""
        bbox = OCRBoundingBox(x=0, y=0, width=100, height=20)
        blocks = [
            OCRTextBlock(text="Hello", confidence=0.9, bbox=bbox),
            OCRTextBlock(text="World", confidence=0.9, bbox=bbox),
        ]
        response = OCRResponse(
            text="Hello World",
            text_blocks=blocks,
            tables=[],
            confidence=0.9,
        )
        assert response.full_text == "Hello\nWorld"

    def test_get_text_by_region(self):
        """Test region-based text extraction."""
        blocks = [
            OCRTextBlock(
                text="In region",
                confidence=0.9,
                bbox=OCRBoundingBox(x=50, y=50, width=100, height=20),
            ),
            OCRTextBlock(
                text="Outside",
                confidence=0.9,
                bbox=OCRBoundingBox(x=500, y=500, width=100, height=20),
            ),
        ]
        response = OCRResponse(
            text="",
            text_blocks=blocks,
            tables=[],
            confidence=0.9,
        )

        in_region = response.get_text_by_region(x=0, y=0, width=200, height=100)
        assert len(in_region) == 1
        assert in_region[0].text == "In region"


class TestLLMGatewayConfig:
    """Tests for LLM gateway configuration."""

    def test_provider_models_defined(self):
        """Test that provider models are defined."""
        assert LLMProvider.OLLAMA in LLMGateway.PROVIDER_MODELS
        assert LLMProvider.OPENAI in LLMGateway.PROVIDER_MODELS
        assert LLMProvider.ANTHROPIC in LLMGateway.PROVIDER_MODELS

    def test_model_types_available(self):
        """Test that all model types are available."""
        for provider in LLMGateway.PROVIDER_MODELS:
            models = LLMGateway.PROVIDER_MODELS[provider]
            assert "default" in models
            assert "medical" in models
            assert "vision" in models


class TestOCRGatewayProviders:
    """Tests for OCR gateway provider support."""

    def test_paddleocr_provider_enum(self):
        """Test PaddleOCR provider enum."""
        assert OCRProvider.PADDLEOCR.value == "paddleocr"

    def test_azure_di_provider_enum(self):
        """Test Azure DI provider enum."""
        assert OCRProvider.AZURE_DI.value == "azure_di"

    def test_tesseract_provider_enum(self):
        """Test Tesseract provider enum."""
        assert OCRProvider.TESSERACT.value == "tesseract"
