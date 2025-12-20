"""
Embedding Service
Text embeddings for semantic search
Source: https://platform.openai.com/docs/guides/embeddings
Verified: 2025-11-14
"""

from openai import AsyncOpenAI

from src.api.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Embedding service supporting any OpenAI-compatible API.

    Evidence: Vector embeddings for semantic similarity search
    Source: https://platform.openai.com/docs/guides/embeddings
    Verified: 2025-11-14
    """

    def __init__(self):
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
        )
        logger.info(
            f"Embedding service initialized: {settings.EMBEDDING_PROVIDER} ({settings.EMBEDDING_MODEL})"
        )

    async def create_embedding(self, text: str) -> list[float]:
        """
        Create embedding vector for a text.

        Args:
            text: Input text

        Returns:
            Embedding vector (list of floats)

        Evidence: Text embeddings capture semantic meaning
        Source: https://platform.openai.com/docs/guides/embeddings/what-are-embeddings
        Verified: 2025-11-14
        """
        response = await self.client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=text,
        )

        embedding = response.data[0].embedding

        logger.info(f"Created embedding: {len(embedding)} dimensions")

        return embedding

    async def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Create embedding vectors for multiple texts (batch).

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Evidence: Batch processing for efficiency
        Source: https://platform.openai.com/docs/guides/embeddings/use-cases
        Verified: 2025-11-14
        """
        response = await self.client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=texts,
        )

        embeddings = [item.embedding for item in response.data]

        logger.info(f"Created {len(embeddings)} embeddings")

        return embeddings

    async def cosine_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0.0 to 1.0)

        Evidence: Cosine similarity for vector comparison
        Source: https://en.wikipedia.org/wiki/Cosine_similarity
        Verified: 2025-11-14
        """
        import numpy as np

        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        return float(similarity)


# Global embedding instance
embedding_service = EmbeddingService()
