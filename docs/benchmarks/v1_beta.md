# Benchmark Baseline: v1.0-beta Release

This document defines the frozen historical baseline benchmark metrics and configurations established for the Graphyra V1.0-beta release. Future code refactoring, adapters, and retrieval modifications will be validated against this baseline to check for regressions.

---

## 1. Baseline Configuration Profile

The benchmark baseline runs under the **Production Profile** defaults structured in `graphyra/config/`:

| Subsystem | Configuration Object | Key Parameter Values |
| :--- | :--- | :--- |
| **Traversal** | `DEFAULT_TRAVERSAL_POLICY` | `max_depth = 2`, `entity_budget = 75`, `chunk_budget = 150`, `total_budget = 100`, `per_seed_budget = 25` |
| **Ranking** | `DEFAULT_RANKING_POLICY` | `top_k = 5`, `rrf_k = 60`, `strategy = "graph_centric"` |
| **BM25** | `DEFAULT_BM25_*` | `k1 = 1.5`, `b = 0.75`, `enable_stopwords = True` |
| **Semantic** | `DEFAULT_SEMANTIC_CONFIG` | `provider = "sentence-transformers"`, `model = "all-MiniLM-L6-v2"`, `top_k = 10` |
| **Chunking** | `DEFAULT_CHUNK_POLICY` | `target_words = 250`, `minimum_words = 120`, `maximum_words = 400` |

---

## 2. Frozen Evaluation Metrics

* **Knowledge Snapshot**: `genshin-1000-seeded` (Scraped and parsed wiki documents containing normalized relationships)
* **High-Confidence Queries**: `100` queries

| Performance Metric | Baseline Value (v1.0-beta) | Target Success Threshold |
| :--- | :---: | :---: |
| **Average Candidate Pool size** | 25.77 chunks | 50.0 to 200.0 (soft target) |
| **Recall@10** | **38.5%** | $\ge 35.0\%$ |
| **MRR** | **0.335** | $\ge 0.300$ |
| **Average Query Latency** | **9.78 ms** | $< 15.0$ ms |
| **SQL Queries (Active Traversal)** | **0.0** | Exactly `0.0` (100% Cache Hit) |
| **Disconnect Rate** | 14.96% | $< 18.0\%$ |

---

## 3. Caching & Memory Telemetry

Measured on 100 benchmark queries using the production default cache configuration:

* **Warm-up Startup Cost**: `526.9 ms` (Average duration to compile repository cache states)
* **Memory RSS Overhead**: `0.0 MB` (Minimal local index dictionary footprint)
* **Average Query Latency (No Cache)**: `26.74 ms`
* **Average Query Latency (Cache Enabled)**: `11.27 ms` (**57.9% Latency Reduction**)
* **SQL Queries (No Cache)**: `29.6` queries per request
* **SQL Queries (Cache Enabled)**: `0.0` queries during BFS traversal (**100% DB query elimination**)
