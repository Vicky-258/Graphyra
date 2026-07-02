from abc import ABC, abstractmethod
from typing import List, Tuple
from models.traversal_models import CandidateEvidence


class RerankerProvider(ABC):
    """
    Abstract provider contract for high-precision reranking models.
    Decouples the ranking pipeline from specific model runtimes (CrossEncoder, API, ONNX).
    """
    @abstractmethod
    def rerank(self, query: str, candidates: List[CandidateEvidence]) -> List[CandidateEvidence]:
        pass


class CrossEncoderReranker(RerankerProvider):
    """
    Reference implementation wrapping HuggingFace CrossEncoder models.
    Lazy-loaded to ensure fast, CPU-friendly initialization during testing.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name, device=self.device)
        return self._model

    def rerank(self, query: str, candidates: List[CandidateEvidence]) -> List[CandidateEvidence]:
        if not candidates:
            return candidates

        # Build query-candidate content pairs
        pairs: List[Tuple[str, str]] = [(query, c.content) for c in candidates]
        
        # Predict pairwise scores
        scores = self.model.predict(pairs)
        
        # Enrich candidate instances
        for idx, score in enumerate(scores):
            candidates[idx].reranker_score = float(score)

        # Sort and return by reranker_score descending (ID fallback for determinism)
        return sorted(
            candidates,
            key=lambda c: (c.reranker_score if c.reranker_score is not None else -float("inf"), c.id),
            reverse=True
        )
