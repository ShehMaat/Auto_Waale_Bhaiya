import hashlib
from typing import List

from packages.llm.provider import LLMProvider


class EmbeddingService:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        # Assuming OpenAI text-embedding-3-small style dimension by default
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimension = 1536
        self.embedding_version = "v1"

    def embed_text(self, text: str) -> List[float]:
        """Generate a vector embedding for the given text."""
        # Simple wrapper over llm provider embed
        # In a real setup, we might batch or cache here, but for now
        # the caching is handled by the caller checking DB.
        return self.llm.embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        return [self.embed_text(t) for t in texts]

    def build_content_hash(self, text: str) -> str:
        """Create a reproducible hash of text for caching."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
