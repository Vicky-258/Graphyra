from typing import List
from semantic.providers import EmbeddingProvider


class EmbeddingEngine:

    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    def get_query_embedding(self, query: str) -> List[float]:
        return self.provider.embed_text(query)

    def get_chunks_embeddings(self, chunks: List[str]) -> List[List[float]]:
        return self.provider.embed_batch(chunks)

    def get_dimension(self) -> int:
        return self.provider.get_dimension()
