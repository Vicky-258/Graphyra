# Graphyra Configuration Guide

Graphyra provides a modular, fully configurable settings subsystem under `graphyra/config/`. All parameters are backed by empirical benchmark-proven defaults but remain fully overrideable at runtime via public constructors and configuration objects.

---

## 1. Configuration Package Architecture

Instead of global constants or environment variables, settings are encapsulated as standard Python objects:

```text
graphyra/
    config/
        __init__.py          # Export endpoints & version metadata
        traversal.py         # Stateful search & priority heap bounds
        retrieval.py         # Evidence collection limits
        ingestion.py         # Canonical resolver defaults
        semantic.py          # Vector provider & model weights
        ranking.py           # BM25 & Ranker policies
        chunking.py          # Paragraph splitter token targets
```

---

## 2. Configuration Subsystems

### 2.1 Traversal Config (`graphyra.config.traversal`)

Defines parameters for the stateful query-time search loop inside the Graph Traversal Engine.

* **`DEFAULT_TRAVERSAL_POLICY`**: An instance of `TraversalPolicy` with the following parameters:
  * `max_depth` (int, default `2`): Limits path hop length from seed query nodes.
  * `entity_budget` (int, default `30`): Max unique entities visited globally during search.
  * `chunk_budget` (int, default `20`): Max unique text chunks visited globally during search.
  * `search_policy_type` (str, default `"best_first"`): Pluggable search strategy (`"best_first"`, `"fifo"`).
  * `momentum_alpha` (float, default `0.7`): Parent state priority decay factor.
  * `expansion_beta` (float, default `0.2`): Balance weight between immediate relevance (MRV) and exploration potential (EP).
  * `consecutive_misses_limit` (int, default `5`): Max consecutive steps without finding accepted chunks before search convergence.
  * `min_priority_threshold` (float, default `0.1`): Minimum state priority threshold.
  * `acceptance_margin` (float, default `0.05`): Dynamic threshold multiplier above the Expansion Context Baseline (ECB).
  * `query_alignment_weight` (float, default `0.45`): Weight for the QA score in MRV.
  * `context_continuity_weight` (float, default `0.30`): Weight for the CC score in MRV.
  * `novelty_weight` (float, default `0.10`): Weight for the Novelty score in MRV.
  * `expansion_potential_weight` (float, default `0.15`): Weight for the EP score in MRV.

### 2.2 Retrieval Config (`graphyra.config.retrieval`)

Specifies options for the main query coordinator.

* **`DEFAULT_RETRIEVAL_CONFIG`**: An instance of `RetrievalConfig`:
  * `evidence_limit` (int, default `20`): Maximum candidate evidence chunks returned.
  * `return_candidates` (bool, default `False`): Returns raw unranked candidates.
  * `return_ranked` (bool, default `False`): Returns intermediate ranking scores.

### 2.3 Ingestion Config (`graphyra.config.ingestion`)

Controls entity type defaults during document ingestion.

* **`DEFAULT_INGESTION_ENTITY_TYPE`** (default `EntityType.CONCEPT`): Fallback type for newly discovered anchors.

### 2.4 Semantic Config (`graphyra.config.semantic`)

Configures vector similarity search and candidate fusion.

* **`DEFAULT_SEMANTIC_CONFIG`**: An instance of `SemanticConfig`:
  * `enabled` (bool, default `True`): Activates vector candidate lookup.
  * `provider` (str, default `"sentence-transformers"`): Adapter wrapper identifier.
  * `model` (str, default `"all-MiniLM-L6-v2"`): Embedding transformer model key.
  * `backend` (str, default `"numpy"`): Embedding computation engine.
  * `top_k` (int, default `10`): Number of closest chunks extracted from semantic index.
  * `batch_size` (int, default `64`): Chunk size parsed during incremental index builds.
  * `direct_match_weight` (float, default `1.0`): Multiplier for exact entity match score.
  * `semantic_match_weight` (float, default `0.8`): Multiplier for semantic match score.

### 2.5 Ranking Config (`graphyra.config.ranking`)

Specifies hybrid ranker policies.

* **`DEFAULT_RANKING_POLICY`**: An instance of `RankingPolicy`:
  * `top_k` (int, default `5`): Chunks returned in visualizer subgraphs.
  * `rerank_top_k` (int, default `3`): Candidates passed to precision cross-encoders.
  * `enable_bm25` (bool, default `True`): Enables BM25 lexical scorer.
  * `enable_semantic` (bool, default `True`): Enables semantic scorer.
  * `enable_reranker` (bool, default `False`): Enables rerankers.
  * `strategy` (str, default `"graph_centric"`): Signal combination strategy.
  * `traversal_weight` (float, default `1.0`)
  * `bm25_weight` (float, default `0.15`)
  * `semantic_weight` (float, default `0.20`)
  * `graph_centric_threshold` (float, default `0.8`)
  * `graph_centric_bonus` (float, default `0.1`)

---

## 3. How to Override Defaults

All constructors and public methods support optional policy injections. If no policy is supplied, they fall back to the default configuration.

### Example: Customizing Traversal Parameters during Querying

```python
from graphyra.engine import Graphyra
from graphyra.models.traversal_models import TraversalPolicy, RetrievalConfig

# Initialize engine
graphyra_engine = Graphyra(db_path="graphyra.db")

# Define custom stateful search policy
custom_policy = TraversalPolicy(
    max_depth=3,
    entity_budget=50,
    chunk_budget=100,
    momentum_alpha=0.6,
    acceptance_margin=0.08
)

# Execute query with custom parameters override
results = graphyra_engine.retrieve(
    question="What is the relation between A and B?",
    config=RetrievalConfig(evidence_limit=15)
)
```
