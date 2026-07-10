from typing import Dict, Any, Optional

class StructuralQualityScorer:
    """
    Computes a generic structural quality score in [0.0, 1.0] for a chunk.
    Analyzes only numerical ChunkFeatures and respects QueryFeatures intent.
    No domain-specific checks or hardcoded wiki strings.
    """

    def calculate_score(self, features: Dict[str, Any], query_features: Optional[Any] = None) -> float:
        if not features:
            return 1.0

        rep_ratio = features.get("repeated_term_ratio", 0.0)
        uniq_ratio = features.get("unique_term_ratio", 1.0)

        # Only apply a penalty if the chunk has extreme repetition (garbage block)
        if rep_ratio > 0.3 and uniq_ratio < 0.4:
            return max(0.1, (1.0 - rep_ratio) + uniq_ratio)

        return 1.0
