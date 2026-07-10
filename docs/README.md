# Graphyra Documentation

Welcome to the official technical documentation for **Graphyra** — an entity-centric, graph-guided evidence retrieval engine designed to navigate interconnected knowledge databases, resolve identities, and extract structured candidate evidence for downstream reasoning traces.

This documentation folder provides detailed breakdowns of all architectural subsystems, classes, database schemas, and integration pipelines in a format suitable for production systems.

---

## Documentation Registry

| Module Documentation | Target Subsystems | Key Concepts Covered |
| :--- | :--- | :--- |
| 🏗️ [Architecture Overview](architecture.md) | Whole System, Boundary layers | System Topology, Data Flow, Sequence diagram, genshin-adapter boundary |
| 📥 [Ingestion Subsystem](ingestion.md) | `ingestion/`, parsing, chunking | Paragraph-first segmentation, Synonym alias mappings, Mention Extractors |
| 🗄️ [Storage Subsystem](storage.md) | `storage/`, `models/` | Decoupled Repository pattern, GraphRepository |
| 🗄️ [Database Schema Reference](storage_schema.md) | `storage/` repositories | SQLite schema fields, indices, foreign keys, and relationships |
| 🛣️ [Traversal & Retrieval](traversal_and_retrieval.md) | `traversal_engine.py`, `retrieval/` | Priority-driven search, ECB baseline pruning, Priority propagation, Subgraphs |
| 🛣️ [Retrieval Pipeline Walkthrough](retrieval_pipeline.md) | engine pipeline | End-to-end trace of a query life cycle from input to LLM context |
| 🧠 [Semantic Layer](semantic_search.md) | `semantic/`, Vector databases | DTOs, VectorIndex persistence, Model drift check, Candidate Fusion engine |
| 🌐 [Web Server & REST APIs](web_api.md) | `server.py`, `utils/jobs.py` | API specs, JSON visualizer payloads, Background job queue runners |
| ⚙️ [Configuration Guide](configuration.md) | `config/` | Centralized defaults configuration objects, overrides, and versions |
| 💡 [Core Philosophy](philosophy.md) | Philosophy | System design values, explicit relations, RAG alternatives |
| 🔌 [Plugin Development Guide](plugin_development.md) | Sibling adapters | Ingestion directives, custom adapter factories, and pluggable strategies |
| 📊 [Benchmark baseline (v1.0-beta)](benchmarks/v1_beta.md) | Benchmarks | Frozen baseline evaluation metrics, caching benefits, and test targets |
| **[Forensic Investigation Report](../brain/6a40691a-2ec3-435e-9361-ffc44b184e01/forensic_investigation.md)** | Diagnostics | Forensic verification of stateful search loop, budgets, and priority decay |

---

## Codebase Directory Structure

```text
Graphyra/ (Core Repository)
├── docs/                             # Technical Documentation Suite
│   ├── ECOSYSTEM.md                  # Project boundaries & Guidelines
│   ├── README.md                     # Registry index
│   └── ...                           # Module guides
├── graphyra/                         # Library Package Root
│   ├── config/                       # Centralized default configurations
│   │   ├── __init__.py
│   │   └── ...
│   ├── ingestion/                    # Paragraph segmentation & pipeline
│   │   └── pipeline.py               # Ingestion orchestrator
│   ├── interfaces/                   # Base adapter contracts & models
│   ├── models/                       # Traversal models & type classes
│   ├── plugins/                      # Pluggable adapter registry system
│   ├── retrieval/                    # Search & ranking strategies
│   │   ├── ranking/                  # BM25, Semantic & Hybrid Rankers
│   │   └── traversal/                # Traversal Policies
│   ├── semantic/                     # Vector indexing & search package
│   ├── storage/                      # Persistence SQLite layer (Repositories)
│   ├── utils/                        # DB Seeder & Graph assemblers
│   ├── engine.py                     # Main DI query resolver entrypoint
│   ├── traversal_engine.py           # Stateful traversal engine
│   └── subgraph_builder.py           # Context subgraph constructor
├── tests/                            # Core pytest unit tests suite
└── pyproject.toml                    # Poetry/UV build dependency metadata
```
