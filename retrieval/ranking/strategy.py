from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

# Local DTO import
from models.traversal_models import CandidateEvidence


@dataclass
class RankingResult:
    candidate: CandidateEvidence
    final_score: float
    explanation: str = ""


class RankingStrategy(ABC):
    @abstractmethod
    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        """
        Scores candidates dynamically using pre-normalized signals inside candidate.signals.
        Returns a list of RankingResult objects.
        """
        pass


class RRFStrategy(RankingStrategy):
    """
    Strategy 1: Reciprocal Rank Fusion (Baseline).
    Scores candidates based on their ranks in individual scorers.
    """
    def __init__(self, k: int = 60):
        self.k = k

    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        from retrieval.ranking.fusion import RankFusionEngine
        engine = RankFusionEngine(k=self.k)
        fused = engine.combine(candidates, active_rankings or [])
        
        results = []
        for idx, c in enumerate(fused):
            val = c.rrf_score if c.rrf_score is not None else (1.0 / (self.k + idx + 1))
            results.append(RankingResult(
                candidate=c,
                final_score=val,
                explanation=f"Reciprocal Rank Fusion (k={self.k}) score: {val:.6f}."
            ))
        return results


class TraversalPriorityStrategy(RankingStrategy):
    """
    Strategy 2: Traversal Priority.
    Traversal remains the dominant signal. Lexical and semantic act as minor bonus parameters.
    """
    def __init__(self, alpha: float = 0.15, beta: float = 0.20):
        self.alpha = alpha
        self.beta = beta

    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        results = []
        for c in candidates:
            signals = getattr(c, "signals", {})
            trav = signals.get("traversal", 0.0)
            bm25 = signals.get("bm25", 0.0)
            sem = signals.get("semantic", 0.0)
            
            final = trav + self.alpha * bm25 + self.beta * sem
            explanation = (
                f"Traversal priority: Trav ({trav:.3f}) + "
                f"alpha*BM25 ({self.alpha}*{bm25:.3f}) + "
                f"beta*Sem ({self.beta}*{sem:.3f}) = {final:.4f}."
            )
            results.append(RankingResult(candidate=c, final_score=final, explanation=explanation))
        return results


class WeightedScoreStrategy(RankingStrategy):
    """
    Strategy 3: Weighted Linear Combination.
    Computes a weighted sum of all signals using configurable weights.
    """
    def __init__(self, trav_w: float = 0.50, bm25_w: float = 0.25, sem_w: float = 0.25):
        self.trav_w = trav_w
        self.bm25_w = bm25_w
        self.sem_w = sem_w

    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        results = []
        for c in candidates:
            signals = getattr(c, "signals", {})
            trav = signals.get("traversal", 0.0)
            bm25 = signals.get("bm25", 0.0)
            sem = signals.get("semantic", 0.0)
            
            final = (self.trav_w * trav) + (self.bm25_w * bm25) + (self.sem_w * sem)
            explanation = (
                f"Weighted linear combination: "
                f"Trav ({self.trav_w}*{trav:.3f}) + "
                f"BM25 ({self.bm25_w}*{bm25:.3f}) + "
                f"Sem ({self.sem_w}*{sem:.3f}) = {final:.4f}."
            )
            results.append(RankingResult(candidate=c, final_score=final, explanation=explanation))
        return results


class TraversalOnlyStrategy(RankingStrategy):
    """
    Strategy 4: Traversal Only.
    Ranks candidates exclusively by traversal score.
    """
    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        results = []
        for c in candidates:
            signals = getattr(c, "signals", {})
            trav = signals.get("traversal", 0.0)
            explanation = f"Traversal only: {trav:.4f}."
            results.append(RankingResult(candidate=c, final_score=trav, explanation=explanation))
        return results


class LexicalOnlyStrategy(RankingStrategy):
    """
    Strategy 5: Lexical Only (BM25).
    Ranks candidates exclusively by lexical overlap score.
    """
    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        results = []
        for c in candidates:
            signals = getattr(c, "signals", {})
            bm25 = signals.get("bm25", 0.0)
            explanation = f"Lexical (BM25) only: {bm25:.4f}."
            results.append(RankingResult(candidate=c, final_score=bm25, explanation=explanation))
        return results


class SemanticOnlyStrategy(RankingStrategy):
    """
    Strategy 6: Semantic Only.
    Ranks candidates exclusively by semantic similarity.
    """
    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        results = []
        for c in candidates:
            signals = getattr(c, "signals", {})
            sem = signals.get("semantic", 0.0)
            explanation = f"Semantic only: {sem:.4f}."
            results.append(RankingResult(candidate=c, final_score=sem, explanation=explanation))
        return results


class GraphCentricStrategy(RankingStrategy):
    """
    Strategy 7: Graph Centric Strategy.
    If TraversalScore >= threshold, Traversal dominates (lexical/semantic break ties).
    Else, falls back to a weighted combination of all three.
    """
    def __init__(
        self,
        threshold: float = 0.8,
        bonus: float = 0.1,
        trav_w: float = 0.50,
        bm25_w: float = 0.25,
        sem_w: float = 0.25
    ):
        self.threshold = threshold
        self.bonus = bonus
        self.trav_w = trav_w
        self.bm25_w = bm25_w
        self.sem_w = sem_w

    def score(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        active_rankings: Optional[List[List[CandidateEvidence]]] = None
    ) -> List[RankingResult]:
        results = []
        for c in candidates:
            signals = getattr(c, "signals", {})
            trav = signals.get("traversal", 0.0)
            bm25 = signals.get("bm25", 0.0)
            sem = signals.get("semantic", 0.0)
            
            if trav >= self.threshold:
                # Traversal dominates, tie-breaker is built from BM25 + Semantic
                tie_breaker = self.bonus * (0.5 * bm25 + 0.5 * sem)
                final = trav + tie_breaker
                explanation = (
                    f"GraphCentric: Traversal dominates ({trav:.3f} >= {self.threshold}). "
                    f"Tie-breaker bonus: {tie_breaker:.4f}."
                )
            else:
                final = (self.trav_w * trav) + (self.bm25_w * bm25) + (self.sem_w * sem)
                explanation = (
                    f"GraphCentric: Traversal below threshold ({trav:.3f} < {self.threshold}). "
                    f"Weighted fallback: {final:.4f}."
                )
            results.append(RankingResult(candidate=c, final_score=final, explanation=explanation))
        return results
