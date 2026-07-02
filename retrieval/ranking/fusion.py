from typing import List, Dict
from models.traversal_models import CandidateEvidence


class RankFusionEngine:
    """
    Combines independent rankings using Reciprocal Rank Fusion (RRF).
    Avoids score mapping/normalization issues by evaluating candidate lists.
    """
    def __init__(self, k: int = 60):
        self.k = k

    def combine(
        self,
        candidates: List[CandidateEvidence],
        rankings: List[List[CandidateEvidence]]
    ) -> List[CandidateEvidence]:
        if not candidates:
            return candidates

        # 1. Initialize RRF scores
        rrf_scores = {c.id: 0.0 for c in candidates}

        # 2. Accumulate reciprocal ranks across all signal lists
        for rank_list in rankings:
            for rank_idx, candidate in enumerate(rank_list):
                rank = rank_idx + 1
                if candidate.id in rrf_scores:
                    rrf_scores[candidate.id] += 1.0 / (self.k + rank)

        # 3. Enrich candidates with computed rrf_score
        for candidate in candidates:
            candidate.rrf_score = rrf_scores[candidate.id]

        # 4. Sort and return candidates by rrf_score descending
        # Ensure a deterministic fallback sorting based on ID strings if scores are identical
        return sorted(
            candidates,
            key=lambda c: (c.rrf_score if c.rrf_score is not None else 0.0, c.id),
            reverse=True
        )
