from graphyra.retrieval.ranking.policy import RankingPolicy

DEFAULT_RANKING_POLICY = RankingPolicy(
    top_k=5,
    rerank_top_k=3,
    enable_bm25=True,
    enable_semantic=True,
    enable_reranker=False,
    rrf_k=60,
    strategy="graph_centric",
    traversal_weight=1.0,
    bm25_weight=0.15,
    semantic_weight=0.20,
    graph_centric_threshold=0.8,
    graph_centric_bonus=0.1
)

# BM25 Lexical Scorer Defaults
DEFAULT_BM25_K1 = 1.5
DEFAULT_BM25_B = 0.75
DEFAULT_BM25_ENABLE_STOPWORDS = True
