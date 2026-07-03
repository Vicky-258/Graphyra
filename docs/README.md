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
Graphyra/ (Core Repository)
├── docs/                             # Technical Documentation Suite
│   ├── ECOSYSTEM.md                  # Project boundaries & Guidelines
│   ├── README.md                     # Registry index
│   └── ...                           # Module guides
├── graphyra/                         # Library Package Root
│   ├── ingestion/                    # Paragraph segmentation & pipeline
│   │   ├── crawler.py                # Domain-agnostic crawl orchestrator
│   │   └── pipeline.py               # Ingestion orchestrator
│   ├── interfaces/                   # Base adapter contracts & models
│   ├── models/                       # Traversal models & type classes
│   ├── retrieval/                    # Search & ranking strategies
│   │   ├── ranking/                  # BM25, Semantic & Hybrid Rankers
│   │   └── traversal/                # Traversal Policies
│   ├── semantic/                     # Vector indexing & search package
│   ├── storage/                      # Persistence SQLite layer (Repositories)
│   ├── utils/                        # DB Seeder & Graph assemblers
│   ├── engine.py                     # Main DI query resolver entrypoint
│   ├── traversal_engine.py           # In-memory traversal BFS engine
│   └── subgraph_builder.py           # Context subgraph constructor
├── tests/                            # Core pytest unit tests suite
└── pyproject.toml                    # Poetry/UV build dependency metadata
```
