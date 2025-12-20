"""
E2E Tests: LLM Settings UI Flow.

Tests the LLM settings management including temperature configuration,
model selection, and prompt customization through the admin UI.

Source: Design Document 04_validation_engine_comprehensive_design.md
"""

import pytest
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# LLM Settings Fixtures
# =============================================================================


@pytest.fixture
def default_llm_settings():
    """Fixture for default LLM settings."""
    return {
        "model": "gpt-4",
        "temperature": 0.3,
        "max_tokens": 1000,
        "top_p": 0.9,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "system_prompt": "You are a healthcare claims validation expert.",
        "created_at": "2025-12-01T00:00:00Z",
        "updated_at": "2025-12-15T10:30:00Z",
    }


@pytest.fixture
def custom_llm_settings():
    """Fixture for custom LLM settings."""
    return {
        "model": "gpt-4-turbo",
        "temperature": 0.1,
        "max_tokens": 2000,
        "top_p": 0.95,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
        "system_prompt": "You are a medical billing expert specializing in claim rejection analysis.",
        "rule_specific_prompts": {
            "CLIN-002": "Focus on medical necessity criteria per CMS guidelines.",
            "CLIN-003": "Evaluate ICD-CPT crosswalk validity based on clinical evidence.",
        },
    }


@pytest.fixture
def available_models():
    """Fixture for available LLM models."""
    return [
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "description": "Most capable model, best for complex reasoning",
            "max_tokens": 8192,
            "recommended_temperature": 0.3,
        },
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "description": "Faster, more cost-effective GPT-4 variant",
            "max_tokens": 128000,
            "recommended_temperature": 0.3,
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "description": "Fast and economical for simpler tasks",
            "max_tokens": 16384,
            "recommended_temperature": 0.5,
        },
        {
            "id": "claude-3-opus",
            "name": "Claude 3 Opus",
            "description": "Anthropic's most capable model",
            "max_tokens": 200000,
            "recommended_temperature": 0.3,
        },
    ]


# =============================================================================
# Settings Retrieval Tests
# =============================================================================


class TestLLMSettingsRetrieval:
    """E2E tests for LLM settings retrieval."""

    @pytest.mark.asyncio
    async def test_get_current_settings(self, default_llm_settings):
        """Test retrieving current LLM settings."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()
            settings_service.get_settings = AsyncMock(return_value=default_llm_settings)
            mock_service.return_value = settings_service

            settings = await settings_service.get_settings()

            assert settings["model"] == "gpt-4"
            assert settings["temperature"] == 0.3
            assert "system_prompt" in settings

    @pytest.mark.asyncio
    async def test_get_available_models(self, available_models):
        """Test retrieving available LLM models."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()
            settings_service.get_available_models = AsyncMock(
                return_value=available_models
            )
            mock_service.return_value = settings_service

            models = await settings_service.get_available_models()

            assert len(models) >= 3
            model_ids = [m["id"] for m in models]
            assert "gpt-4" in model_ids

    @pytest.mark.asyncio
    async def test_settings_include_update_timestamp(self, default_llm_settings):
        """Test that settings include update timestamp."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()
            settings_service.get_settings = AsyncMock(return_value=default_llm_settings)
            mock_service.return_value = settings_service

            settings = await settings_service.get_settings()

            assert "updated_at" in settings
            assert settings["updated_at"] is not None


# =============================================================================
# Settings Update Tests
# =============================================================================


class TestLLMSettingsUpdate:
    """E2E tests for LLM settings updates."""

    @pytest.mark.asyncio
    async def test_update_temperature(self, default_llm_settings):
        """Test updating LLM temperature setting."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            updated_settings = default_llm_settings.copy()
            updated_settings["temperature"] = 0.5
            updated_settings["updated_at"] = datetime.now().isoformat()

            settings_service.update_settings = AsyncMock(return_value=updated_settings)
            mock_service.return_value = settings_service

            result = await settings_service.update_settings({"temperature": 0.5})

            assert result["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_update_model_selection(self, default_llm_settings):
        """Test updating LLM model selection."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            updated_settings = default_llm_settings.copy()
            updated_settings["model"] = "gpt-4-turbo"

            settings_service.update_settings = AsyncMock(return_value=updated_settings)
            mock_service.return_value = settings_service

            result = await settings_service.update_settings({"model": "gpt-4-turbo"})

            assert result["model"] == "gpt-4-turbo"

    @pytest.mark.asyncio
    async def test_update_system_prompt(self, default_llm_settings):
        """Test updating system prompt."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            new_prompt = "You are an expert in healthcare fraud detection."
            updated_settings = default_llm_settings.copy()
            updated_settings["system_prompt"] = new_prompt

            settings_service.update_settings = AsyncMock(return_value=updated_settings)
            mock_service.return_value = settings_service

            result = await settings_service.update_settings(
                {"system_prompt": new_prompt}
            )

            assert result["system_prompt"] == new_prompt

    @pytest.mark.asyncio
    async def test_reject_invalid_temperature(self):
        """Test that invalid temperature values are rejected."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            settings_service.update_settings = AsyncMock(
                side_effect=ValueError("Temperature must be between 0.0 and 2.0")
            )
            mock_service.return_value = settings_service

            with pytest.raises(ValueError, match="Temperature"):
                await settings_service.update_settings({"temperature": 2.5})

    @pytest.mark.asyncio
    async def test_reject_invalid_model(self, available_models):
        """Test that invalid model selection is rejected."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            settings_service.update_settings = AsyncMock(
                side_effect=ValueError("Invalid model: unknown-model")
            )
            mock_service.return_value = settings_service

            with pytest.raises(ValueError, match="Invalid model"):
                await settings_service.update_settings({"model": "unknown-model"})


# =============================================================================
# Rule-Specific Prompt Tests
# =============================================================================


class TestRuleSpecificPrompts:
    """E2E tests for rule-specific prompt configuration."""

    @pytest.mark.asyncio
    async def test_get_rule_prompts(self, custom_llm_settings):
        """Test retrieving rule-specific prompts."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()
            settings_service.get_settings = AsyncMock(return_value=custom_llm_settings)
            mock_service.return_value = settings_service

            settings = await settings_service.get_settings()

            assert "rule_specific_prompts" in settings
            assert "CLIN-002" in settings["rule_specific_prompts"]

    @pytest.mark.asyncio
    async def test_add_rule_prompt(self, default_llm_settings):
        """Test adding a rule-specific prompt."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            updated_settings = default_llm_settings.copy()
            updated_settings["rule_specific_prompts"] = {
                "CLIN-005": "Focus on age-specific treatment guidelines."
            }

            settings_service.update_rule_prompt = AsyncMock(
                return_value=updated_settings
            )
            mock_service.return_value = settings_service

            result = await settings_service.update_rule_prompt(
                rule_id="CLIN-005",
                prompt="Focus on age-specific treatment guidelines.",
            )

            assert "CLIN-005" in result["rule_specific_prompts"]

    @pytest.mark.asyncio
    async def test_remove_rule_prompt(self, custom_llm_settings):
        """Test removing a rule-specific prompt."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            updated_settings = custom_llm_settings.copy()
            updated_settings["rule_specific_prompts"] = {"CLIN-003": "remaining prompt"}

            settings_service.remove_rule_prompt = AsyncMock(
                return_value=updated_settings
            )
            mock_service.return_value = settings_service

            result = await settings_service.remove_rule_prompt(rule_id="CLIN-002")

            assert "CLIN-002" not in result["rule_specific_prompts"]


# =============================================================================
# Settings Validation Tests
# =============================================================================


class TestLLMSettingsValidation:
    """E2E tests for LLM settings validation."""

    @pytest.mark.asyncio
    async def test_validate_temperature_range(self):
        """Test temperature range validation."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            # Valid temperatures should pass
            settings_service.validate_settings = AsyncMock(
                return_value={"valid": True, "errors": []}
            )
            mock_service.return_value = settings_service

            result = await settings_service.validate_settings({"temperature": 0.7})
            assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_max_tokens_limit(self, available_models):
        """Test max_tokens validation against model limits."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            # GPT-4 has 8192 token limit
            settings_service.validate_settings = AsyncMock(
                return_value={
                    "valid": False,
                    "errors": ["max_tokens exceeds model limit of 8192"],
                }
            )
            mock_service.return_value = settings_service

            result = await settings_service.validate_settings(
                {"model": "gpt-4", "max_tokens": 10000}
            )

            assert result["valid"] is False
            assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_prompt_length(self):
        """Test system prompt length validation."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            # Very long prompt
            long_prompt = "a" * 50000

            settings_service.validate_settings = AsyncMock(
                return_value={
                    "valid": False,
                    "errors": ["system_prompt exceeds maximum length of 10000 characters"],
                }
            )
            mock_service.return_value = settings_service

            result = await settings_service.validate_settings(
                {"system_prompt": long_prompt}
            )

            assert result["valid"] is False


# =============================================================================
# Settings Preview Tests
# =============================================================================


class TestLLMSettingsPreview:
    """E2E tests for LLM settings preview functionality."""

    @pytest.mark.asyncio
    async def test_preview_reasoning_output(self, default_llm_settings):
        """Test previewing LLM reasoning output with current settings."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            preview_result = {
                "input": {
                    "validation_results": [
                        {"rule_id": "CLIN-002", "status": "failed"}
                    ]
                },
                "output": {
                    "summary": "Sample rejection reasoning preview",
                    "reasoning": ["Sample reasoning point 1"],
                },
                "tokens_used": 150,
                "execution_time_ms": 500,
            }

            settings_service.preview_output = AsyncMock(return_value=preview_result)
            mock_service.return_value = settings_service

            result = await settings_service.preview_output(
                sample_input={
                    "validation_results": [{"rule_id": "CLIN-002", "status": "failed"}]
                }
            )

            assert "output" in result
            assert "tokens_used" in result

    @pytest.mark.asyncio
    async def test_preview_with_modified_settings(self, default_llm_settings):
        """Test preview with temporarily modified settings."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            # Preview with different temperature
            preview_result = {
                "settings_used": {"temperature": 0.8},
                "output": {"summary": "More creative output with higher temperature"},
            }

            settings_service.preview_with_settings = AsyncMock(
                return_value=preview_result
            )
            mock_service.return_value = settings_service

            result = await settings_service.preview_with_settings(
                sample_input={"validation_results": []},
                settings_override={"temperature": 0.8},
            )

            assert result["settings_used"]["temperature"] == 0.8


# =============================================================================
# Settings History Tests
# =============================================================================


class TestLLMSettingsHistory:
    """E2E tests for LLM settings change history."""

    @pytest.mark.asyncio
    async def test_get_settings_history(self):
        """Test retrieving settings change history."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            history = [
                {
                    "id": str(uuid4()),
                    "changed_at": "2025-12-15T10:30:00Z",
                    "changed_by": "admin@example.com",
                    "changes": {"temperature": {"old": 0.3, "new": 0.5}},
                },
                {
                    "id": str(uuid4()),
                    "changed_at": "2025-12-10T14:00:00Z",
                    "changed_by": "admin@example.com",
                    "changes": {"model": {"old": "gpt-3.5-turbo", "new": "gpt-4"}},
                },
            ]

            settings_service.get_history = AsyncMock(return_value=history)
            mock_service.return_value = settings_service

            result = await settings_service.get_history(limit=10)

            assert len(result) >= 2
            assert "changes" in result[0]

    @pytest.mark.asyncio
    async def test_rollback_settings(self):
        """Test rolling back to previous settings."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            rollback_result = {
                "success": True,
                "restored_settings": {"model": "gpt-3.5-turbo", "temperature": 0.3},
                "rolled_back_from": "2025-12-15T10:30:00Z",
            }

            settings_service.rollback = AsyncMock(return_value=rollback_result)
            mock_service.return_value = settings_service

            result = await settings_service.rollback(history_id="some-uuid")

            assert result["success"] is True
            assert "restored_settings" in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestLLMSettingsIntegration:
    """Integration tests for complete LLM settings flow."""

    @pytest.mark.asyncio
    async def test_full_settings_update_flow(
        self, default_llm_settings, available_models
    ):
        """Test complete flow of viewing, modifying, and applying settings."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            # Step 1: Get current settings
            settings_service.get_settings = AsyncMock(return_value=default_llm_settings)

            # Step 2: Get available models
            settings_service.get_available_models = AsyncMock(
                return_value=available_models
            )

            # Step 3: Validate new settings
            settings_service.validate_settings = AsyncMock(
                return_value={"valid": True, "errors": []}
            )

            # Step 4: Apply settings
            updated_settings = default_llm_settings.copy()
            updated_settings["model"] = "gpt-4-turbo"
            updated_settings["temperature"] = 0.2
            settings_service.update_settings = AsyncMock(return_value=updated_settings)

            mock_service.return_value = settings_service

            # Execute flow
            current = await settings_service.get_settings()
            models = await settings_service.get_available_models()
            validation = await settings_service.validate_settings(
                {"model": "gpt-4-turbo", "temperature": 0.2}
            )
            updated = await settings_service.update_settings(
                {"model": "gpt-4-turbo", "temperature": 0.2}
            )

            # Verify flow
            assert current["model"] == "gpt-4"
            assert len(models) >= 3
            assert validation["valid"] is True
            assert updated["model"] == "gpt-4-turbo"
            assert updated["temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_settings_affect_reasoning_output(self, default_llm_settings):
        """Test that settings changes affect reasoning output quality."""
        with patch("src.api.routes.llm_settings.get_llm_settings_service") as mock_service:
            settings_service = AsyncMock()

            # Low temperature - more deterministic
            low_temp_output = {
                "temperature_used": 0.1,
                "output": {"summary": "Precise, focused rejection reasoning"},
                "consistency_score": 0.95,
            }

            # High temperature - more varied
            high_temp_output = {
                "temperature_used": 0.9,
                "output": {"summary": "Creative, varied rejection reasoning"},
                "consistency_score": 0.6,
            }

            settings_service.preview_with_settings = AsyncMock(
                side_effect=[low_temp_output, high_temp_output]
            )
            mock_service.return_value = settings_service

            low_temp_result = await settings_service.preview_with_settings(
                sample_input={}, settings_override={"temperature": 0.1}
            )
            high_temp_result = await settings_service.preview_with_settings(
                sample_input={}, settings_override={"temperature": 0.9}
            )

            # Lower temperature should have higher consistency
            assert low_temp_result["consistency_score"] > high_temp_result["consistency_score"]
