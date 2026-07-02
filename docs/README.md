# Graphyra Documentation

Welcome to the official technical documentation for **Graphyra** — an entity-centric, graph-guided evidence retrieval engine designed to navigate interconnected knowledge databases, resolve identities, and extract structured candidate evidence for downstream reasoning traces.

This documentation folder provides detailed breakdowns of all architectural subsystems, classes, database schemas, and integration pipelines in a format suitable for production systems.

---

## Documentation Registry

| Module Documentation | Target Subsystems | Key Concepts Covered |
| :--- | :--- | :--- |
| 🏗️ [Architecture Overview](architecture.md) | Whole System, Boundary layers | System Topology, Data Flow, Sequence diagram, genshin-adapter boundary |
| 📥 [Ingestion Subsystem](ingestion.md) | `ingestion/`, parsing, chunking | Paragraph-first segmentation, Synonym alias mappings, Mention Extractors |
| 🗄️ [Storage Subsystem](storage.md) | `storage/`, `models/` | SQLite schemas, Decoupled Repository pattern, GraphRepository |
| 🛣️ [Traversal & Retrieval](traversal_and_retrieval.md) | `traversal_engine.py`, `subgraph_builder.py` | BFS path exploration, Traversal scoring formula, Path pruning, Subgraphs |
| 🧠 [Semantic Layer](semantic_search.md) | `semantic/`, Vector databases | DTOs, VectorIndex persistence, Model drift check, Candidate Fusion engine |
| 🌐 [Web Server & REST APIs](web_api.md) | `server.py`, `utils/jobs.py` | API specs, JSON visualizer payloads, Background job queue runners |

---

## Codebase Directory Structure

```text
Graphyra/
├── docs/                             # Project Technical Documentation
├── ingestion/                        # Document segmentation & anchor extraction
│   ├── chunking.py                   # Paragraph-first segment rules
│   ├── mention_extractor.py          # Dictionary & Regex entity matchers
│   └── pipeline.py                   # Ingestion orchestrator
├── storage/                          # Relational SQLite persistence layer
│   ├── sqlite_storage.py             # Schema definition & SQL connection proxies
│   ├── graph_repository.py           # Graph connectivity repository
│   └── chunk_repository.py           # Chunk read/write repository
├── semantic/                         # Vector indexing & search package
│   ├── providers/                    # sentence-transformers & mock adapters
│   ├── index.py                      # Standalone SQLiteVectorIndex persistence
│   ├── indexer.py                    # Sync indexer (incremental/rebuilds)
│   └── fusion.py                     # Candidate fusion scoring
├── graphyra_adapter_genshin/         # External wiki scraping adapter
├── models/                           # Dataclasses & Type contracts
├── engine.py                         # Graphyra DI query entrypoint
├── server.py                         # Web backend, HTTP API, & Job runner
└── tests/                            # Comprehensive unit test suites
```
