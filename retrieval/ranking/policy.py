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
