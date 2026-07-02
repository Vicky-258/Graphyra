import hashlib
from typing import List
from semantic.providers.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic pseudo-random embedding provider.
    Ensures consistent, repeatable outputs for testing and offline execution.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        import numpy as np
        h = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(h[:4], "little"))
        vec = rng.normal(size=self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    def get_dimension(self) -> int:
        return self.dimension
