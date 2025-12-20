"""
LLM Service
OpenAI-compatible LLM client (Ollama, OpenAI, Claude, etc.)
Source: https://platform.openai.com/docs/api-reference
Verified: 2025-11-14
"""

from openai import AsyncOpenAI

from src.api.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    LLM service supporting any OpenAI-compatible API.

    Evidence: OpenAI API is widely supported across providers
    - OpenAI: Official API
    - Ollama: Local inference with OpenAI compatibility
    - Claude: Anthropic's OpenAI-compatible endpoint
    Source: https://docs.ollama.com/openai
    Verified: 2025-11-14
    """

    def __init__(self):
        # Initialize OpenAI client
        # Evidence: Async client for non-blocking operations
        # Source: https://github.com/openai/openai-python
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        logger.info(f"LLM service initialized: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")

    async def complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: User prompt
            system_message: Optional system message
            temperature: Sampling temperature (default: from settings)
            max_tokens: Max tokens to generate (default: from settings)

        Returns:
            Generated text

        Evidence: Chat completions API
        Source: https://platform.openai.com/docs/api-reference/chat/create
        Verified: 2025-11-14
        """
        messages: list[dict[str, str]] = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature or settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        )

        completion = response.choices[0].message.content or ""

        logger.info(f"LLM completion generated: {len(completion)} chars")

        return completion

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """
        Multi-turn chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Generated text
        """
        response = await self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature or settings.LLM_TEMPERATURE,
            max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        )

        completion = response.choices[0].message.content or ""

        return completion

    async def stream_complete(
        self,
        prompt: str,
        system_message: str | None = None,
        temperature: float | None = None,
    ):
        """
        Streaming text completion.

        Args:
            prompt: User prompt
            system_message: Optional system message
            temperature: Sampling temperature

        Yields:
            Text chunks as they are generated

        Evidence: Streaming for better UX
        Source: https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream
        Verified: 2025-11-14
        """
        messages: list[dict[str, str]] = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        stream = await self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=temperature or settings.LLM_TEMPERATURE,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Global LLM instance
llm = LLMService()
