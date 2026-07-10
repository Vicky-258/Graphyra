from graphyra.models.traversal_models import TraversalPolicy

DEFAULT_TRAVERSAL_POLICY = TraversalPolicy(
    max_depth=2,
    entity_budget=75,
    chunk_budget=150,
    total_budget=100,
    per_seed_budget=25,
    max_degree_threshold=None,
    enable_scoring=True,
    depth_penalty=0.1,
    min_relevance=0.2,
    relation_weights={
        "mentions": 1.0,
        "links_to": 0.8,
        "contains": 0.7,
        "similar_to": 0.4
    }
)
