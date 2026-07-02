from typing import List, Optional
from models.traversal_models import CandidateEvidence
from retrieval.ranking.policy import RankingPolicy
from retrieval.ranking.bm25 import BM25Scorer
from retrieval.ranking.semantic import SemanticScorer
from retrieval.ranking.fusion import RankFusionEngine
from retrieval.ranking.reranker import RerankerProvider


class EvidenceRanker:
    """
    Coordinates the entire modular evidence ranking pipeline.
    Assembles independent rankings, performs rank fusion, and runs precision reranking.
    """
    def __init__(
        self,
        bm25_scorer: Optional[BM25Scorer] = None,
        semantic_scorer: Optional[SemanticScorer] = None,
        fusion_engine: Optional[RankFusionEngine] = None,
        reranker_provider: Optional[RerankerProvider] = None
    ):
        self.bm25_scorer = bm25_scorer or BM25Scorer()
        self.semantic_scorer = semantic_scorer
        self.fusion_engine = fusion_engine or RankFusionEngine()
        self.reranker_provider = reranker_provider

    def rank(
        self,
        query: str,
        candidates: List[CandidateEvidence],
        policy: Optional[RankingPolicy] = None
    ) -> List[CandidateEvidence]:
        if not candidates:
            return candidates

        pol = policy or RankingPolicy()
        active_rankings = []

        # 1. Structural Traversal Ranking
        # Establish base ranking list sorted by traversal score (ID fallback for determinism)
        traversal_sorted = sorted(
            candidates,
            key=lambda c: (c.best_traversal_score if c.best_traversal_score is not None else 0.0, c.id),
            reverse=True
        )
        active_rankings.append(traversal_sorted)

        # 2. Lexical Relevance Scoring
        if pol.enable_bm25 and self.bm25_scorer:
            self.bm25_scorer.score(query, candidates)
            bm25_sorted = sorted(
                candidates,
                key=lambda c: (c.bm25_score if c.bm25_score is not None else 0.0, c.id),
                reverse=True
            )
            active_rankings.append(bm25_sorted)
        else:
            for c in candidates:
                c.bm25_score = None

        # 3. Conceptual Semantic Scoring
        if pol.enable_semantic and self.semantic_scorer:
            self.semantic_scorer.score(query, candidates)
            semantic_sorted = sorted(
                candidates,
                key=lambda c: (c.semantic_score if c.semantic_score is not None else 0.0, c.id),
                reverse=True
            )
            active_rankings.append(semantic_sorted)
        else:
            for c in candidates:
                c.semantic_score = None

        # 4. Rank Fusion
        # Re-initialize the RankFusionEngine with the policy's RRF constant
        self.fusion_engine.k = pol.rrf_k
        fused = self.fusion_engine.combine(candidates, active_rankings)

        # 5. Precision Reranking
        if pol.enable_reranker and self.reranker_provider:
            # Slice the candidate pool to send only top-K to reranker
            rerank_limit = min(pol.rerank_top_k, len(fused))
            to_rerank = fused[:rerank_limit]
            not_reranked = fused[rerank_limit:]

            # Execute Reranker
            reranked = self.reranker_provider.rerank(query, to_rerank)
            
            # Map rerank results to final_score
            for c in reranked:
                c.final_score = c.reranker_score

            # Assign lower fallback score to non-reranked candidates maintaining RRF order
            min_reranker_score = min((c.reranker_score for c in reranked), default=0.0)
            for idx, c in enumerate(not_reranked):
                c.reranker_score = None
                c.final_score = min_reranker_score - 1.0 - idx

            result = sorted(
                reranked + not_reranked,
                key=lambda c: (c.final_score if c.final_score is not None else -float("inf"), c.id),
                reverse=True
            )
        else:
            # Set reciprocal RRF score as final_score
            for idx, c in enumerate(fused):
                c.reranker_score = None
                c.final_score = c.rrf_score if c.rrf_score is not None else (1.0 / (idx + 1))
            result = fused

        return result
