from dataclasses import dataclass


@dataclass
class RankingPolicy:
    """
    Configures evidence ranking and pruning execution parameters.
    Does not encode manual scoring weights to avoid architectural bias.
    """
    top_k: int = 5
    rerank_top_k: int = 3
    enable_bm25: bool = True
    enable_semantic: bool = True
    enable_reranker: bool = False
    rrf_k: int = 60
    strategy: str = "rrf"
    traversal_weight: float = 1.0
    bm25_weight: float = 0.15
    semantic_weight: float = 0.20
    graph_centric_threshold: float = 0.8
    graph_centric_bonus: float = 0.1
