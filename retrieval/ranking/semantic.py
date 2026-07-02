import numpy as np
from typing import List, Optional
from models.traversal_models import CandidateEvidence
from semantic.providers.base import EmbeddingProvider
from semantic.index import VectorIndex


class SemanticScorer:
    """
    Evaluates conceptual similarity between query and candidate text.
    Reuses existing EmbeddingProvider and VectorIndex database.
    """
    def __init__(self, provider: EmbeddingProvider, index: VectorIndex):
        self.provider = provider
        self.index = index

    def score(self, query: str, candidates: List[CandidateEvidence]) -> List[CandidateEvidence]:
        if not candidates:
            return candidates

        # 1. Generate normalized query embedding
        query_vector = np.array(self.provider.embed_text(query), dtype=np.float32)
        q_norm = np.linalg.norm(query_vector)
        if q_norm > 0:
            query_vector = query_vector / q_norm

        # 2. Fetch candidate embeddings (lookup from VectorIndex, falling back to provider)
        for candidate in candidates:
            vector = None
            if hasattr(self.index, "ids") and hasattr(self.index, "vectors") and self.index.vectors is not None:
                try:
                    idx = self.index.ids.index(candidate.id)
                    vector = self.index.vectors[idx]
                except ValueError:
                    pass

            if vector is None:
                # Fallback to direct embedding if not present in vector index
                raw_vector = self.provider.embed_text(candidate.content)
                vector = np.array(raw_vector, dtype=np.float32)
                c_norm = np.linalg.norm(vector)
                if c_norm > 0:
                    vector = vector / c_norm

            # Normalized cosine similarity is the dot product
            similarity = np.dot(query_vector, vector)
            candidate.semantic_score = float(similarity)

        return candidates
