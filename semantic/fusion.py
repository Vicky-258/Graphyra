from typing import List, Dict
from models.entity import Entity


class CandidateFusionEngine:
    """
    CandidateFusionEngine merges entity matches from exact query search and semantic chunks discovery.
    Removes duplicates, scales matches by configurable weights, and produces ranked seeds.
    """

    def __init__(self, direct_match_weight: float = 1.0, semantic_match_weight: float = 0.8):
        self.direct_match_weight = direct_match_weight
        self.semantic_match_weight = semantic_match_weight

    def fuse_candidates(
        self,
        direct_entities: List[Entity],
        semantic_entities: List[tuple[Entity, float]]
    ) -> List[tuple[Entity, float]]:
        """
        Merges query direct matches and semantic candidates, applying configured weights.
        Returns a ranked list of (Entity, score) traversal seeds.
        """
        fused_scores: Dict[str, tuple[Entity, float]] = {}

        # 1. Process direct entity matches
        for ent in direct_entities:
            score = 1.0 * self.direct_match_weight
            fused_scores[ent.id] = (ent, score)

        # 2. Process semantic entity matches
        for ent, sim in semantic_entities:
            score = sim * self.semantic_match_weight
            if ent.id in fused_scores:
                existing_ent, existing_score = fused_scores[ent.id]
                fused_scores[ent.id] = (existing_ent, max(existing_score, score))
            else:
                fused_scores[ent.id] = (ent, score)

        ranked_seeds = list(fused_scores.values())
        ranked_seeds.sort(key=lambda x: x[1], reverse=True)
        return ranked_seeds
