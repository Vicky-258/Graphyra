from graphyra.models.traversal_models import RetrievalConfig

DEFAULT_RETRIEVAL_CONFIG = RetrievalConfig(
    evidence_limit=20,
    return_candidates=False,
    return_ranked=False
)
