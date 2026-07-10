from graphyra.semantic.config import SemanticConfig

DEFAULT_SEMANTIC_CONFIG = SemanticConfig(
    enabled=True,
    provider="sentence-transformers",
    model="all-MiniLM-L6-v2",
    backend="numpy",
    top_k=10,
    batch_size=64,
    direct_match_weight=1.0,
    semantic_match_weight=0.8
)
