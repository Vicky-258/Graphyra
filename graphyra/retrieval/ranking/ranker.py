from typing import List, Optional
from graphyra.models.traversal_models import CandidateEvidence
from graphyra.retrieval.ranking.policy import RankingPolicy
from graphyra.retrieval.ranking.bm25 import BM25Scorer
from graphyra.retrieval.ranking.semantic import SemanticScorer
from graphyra.retrieval.ranking.fusion import RankFusionEngine
from graphyra.retrieval.ranking.reranker import RerankerProvider


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

        # 4. Score Normalization Preprocessing
        trav_scores = [c.best_traversal_score for c in candidates if c.best_traversal_score is not None]
        trav_min = min(trav_scores, default=0.0)
        trav_max = max(trav_scores, default=1.0)
        trav_denom = (trav_max - trav_min) if (trav_max - trav_min) > 0 else 1.0

        bm25_scores = [c.bm25_score for c in candidates if c.bm25_score is not None]
        bm25_min = min(bm25_scores, default=0.0)
        bm25_max = max(bm25_scores, default=1.0)
        bm25_denom = (bm25_max - bm25_min) if (bm25_max - bm25_min) > 0 else 1.0

        sem_scores = [c.semantic_score for c in candidates if c.semantic_score is not None]
        sem_min = min(sem_scores, default=0.0)
        sem_max = max(sem_scores, default=1.0)
        sem_denom = (sem_max - sem_min) if (sem_max - sem_min) > 0 else 1.0

        for c in candidates:
            raw_t = c.best_traversal_score if c.best_traversal_score is not None else 0.0
            raw_b = c.bm25_score if c.bm25_score is not None else 0.0
            raw_s = c.semantic_score if c.semantic_score is not None else 0.0
            
            c.signals = {
                "traversal": (raw_t - trav_min) / trav_denom if trav_max != trav_min else (1.0 if trav_max > 0 else 0.0),
                "bm25": (raw_b - bm25_min) / bm25_denom if bm25_max != bm25_min else (1.0 if bm25_max > 0 else 0.0),
                "semantic": (raw_s - sem_min) / sem_denom if sem_max != sem_min else (1.0 if sem_max > 0 else 0.0)
            }

        # 5. Resolve & Execute Ranking Strategy
        from graphyra.retrieval.ranking.strategy import RankingStrategy, RRFStrategy, TraversalPriorityStrategy, WeightedScoreStrategy, GraphCentricStrategy
        
        strategy_class = None
        strategy_clean = pol.strategy.lower().replace("_", "").replace("strategy", "")
        for sub in RankingStrategy.__subclasses__():
            sub_clean = sub.__name__.lower().replace("_", "").replace("strategy", "")
            if sub_clean == strategy_clean:
                strategy_class = sub
                break

        if strategy_class is RRFStrategy:
            strategy_inst = RRFStrategy(k=pol.rrf_k)
        elif strategy_class is TraversalPriorityStrategy:
            strategy_inst = TraversalPriorityStrategy(alpha=pol.bm25_weight, beta=pol.semantic_weight)
        elif strategy_class is WeightedScoreStrategy:
            strategy_inst = WeightedScoreStrategy(trav_w=pol.traversal_weight, bm25_w=pol.bm25_weight, sem_w=pol.semantic_weight)
        elif strategy_class is GraphCentricStrategy:
            strategy_inst = GraphCentricStrategy(
                threshold=pol.graph_centric_threshold,
                bonus=pol.graph_centric_bonus,
                trav_w=pol.traversal_weight,
                bm25_w=pol.bm25_weight,
                sem_w=pol.semantic_weight
            )
        elif strategy_class is not None:
            # Dynamic subclass discovery mapping
            import inspect
            sig = inspect.signature(strategy_class.__init__)
            params = sig.parameters
            kwargs = {}
            if "k" in params:
                kwargs["k"] = pol.rrf_k
            if "alpha" in params:
                kwargs["alpha"] = pol.bm25_weight
            if "beta" in params:
                kwargs["beta"] = pol.semantic_weight
            if "threshold" in params:
                kwargs["threshold"] = pol.graph_centric_threshold
            if "bonus" in params:
                kwargs["bonus"] = pol.graph_centric_bonus
            if "trav_w" in params:
                kwargs["trav_w"] = pol.traversal_weight
            if "bm25_w" in params:
                kwargs["bm25_w"] = pol.bm25_weight
            if "sem_w" in params:
                kwargs["sem_w"] = pol.semantic_weight
            strategy_inst = strategy_class(**kwargs)
        else:
            strategy_inst = RRFStrategy(k=pol.rrf_k)

        # Execute Strategy Scoring
        scored_results = strategy_inst.score(query, candidates, active_rankings)
        
        # Unpack strategy scoring results
        for res in scored_results:
            c = res.candidate
            c.final_score = res.final_score
            # Attach explanation to chunk metadata
            if c.chunk and getattr(c.chunk, "metadata", None) is not None:
                c.chunk.metadata["ranking_explanation"] = res.explanation

        # 6. Sort by strategy score
        sorted_candidates = sorted(
            candidates,
            key=lambda cand: cand.final_score if cand.final_score is not None else -float("inf"),
            reverse=True
        )

        # 7. Precision Reranking
        if pol.enable_reranker and self.reranker_provider:
            rerank_limit = min(pol.rerank_top_k, len(sorted_candidates))
            to_rerank = sorted_candidates[:rerank_limit]
            not_reranked = sorted_candidates[rerank_limit:]

            reranked = self.reranker_provider.rerank(query, to_rerank)
            for c in reranked:
                c.final_score = c.reranker_score

            min_reranker_score = min((c.reranker_score for c in reranked), default=0.0)
            for idx, c in enumerate(not_reranked):
                c.reranker_score = None
                c.final_score = min_reranker_score - 1.0 - idx

            result = sorted(
                reranked + not_reranked,
                key=lambda c: c.final_score if c.final_score is not None else -float("inf"),
                reverse=True
            )
        else:
            result = sorted_candidates

        return result
