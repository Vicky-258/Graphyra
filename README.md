# Graphyra — Graph-Guided Retrieval-Augmented Generation (G-RAG) Engine

Graphyra is a production-grade **Graph-Guided Retrieval-Augmented Generation (G-RAG)** engine. Traditional RAG retrieval treats text chunks as isolated vectors, losing structural links and multi-hop traversal contexts. Graphyra solves this by pairing document chunks with a relational reference navigation graph, performing dynamic path scoring to retrieve coherent evidence chains for complex, multi-hop queries.

---

## 🚀 Key Subsystems

1. **Incremental Ingestion Pipeline** (`ingestion/`): Employs a **Paragraph-First** chunking strategy to preserve paragraph context and HTML tables. Uses a compiled **Dictionary Mention Extractor** to map entity synonyms and redirects dynamically.
2. **Decoupled Relational Storage** (`storage/`): Implements SQLite storage patterns using a thread-local proxy session model. Exposes a decoupled `GraphRepository` interface separating SQL queries from graph traversal loops.
3. **Semantic Index & Fusion** (`semantic/`): Maintains a secondary SQLite vector index (`embeddings.db`) isolated from the main knowledge graph. Runs fast in-memory cosine similarities using numpy dot-products. Fuses semantic discovery and direct keyword matches dynamically via `CandidateFusionEngine`.
4. **Scraper Wiki Adapter** (`graphyra-adapter-genshin`): MediaWiki scraping client with revision-diff change detection and synchronizer queues.
5. **Interactive UI Storyboard & Diagnostics Dashboard** (`frontend/`): A Vite + React application providing a matte dark query trace storyboard, structural graph visualization, and an ingestion statistics dashboard displaying metrics histograms.

---

## 📂 Codebase Directory Structure

```text
Graphyra/
├── docs/                             # Full Project Technical Documentation
│   ├── README.md                     # Documentation registry & overview
│   ├── architecture.md               # Topology, boundaries, and query flows
│   ├── ingestion.md                  # Chunk policies & Synonym extractors
│   ├── storage.md                    # Database schemas & proxy proxies
│   ├── traversal_and_retrieval.md     # BFS scoring & CandidateEvidence DTOs
│   └── semantic_search.md            # Vector databases & fusion formulas
├── ingestion/                        # Text chunking & Entity extraction
├── storage/                          # Relational SQLite repositories
├── semantic/                         # Vector database, engines, and fusion
├── graphyra_adapter_genshin/         # External wiki scraping adapter
├── models/                           # Type contracts & Dataclasses
├── frontend/                         # React UI Storyboard & Diagnostics Dashboard
├── engine.py                         # Graphyra composition & retrieval entrypoint
├── server.py                         # HTTP REST API server & job manager
└── index_semantics.py                # Standalone CLI semantic index tool
```

---

## 🛠️ Getting Started

### 1. Database Seeding & CLI Trace
To seed the Sumeru wiki corpus, build the relational tables, run model-drift verification, and execute a CLI reasoning trace, run:
```bash
python main.py
```

### 2. Standalone Semantic Indexing
To generate real `all-MiniLM-L6-v2` Sentence Transformer embeddings for all chunks in the database without running a crawl:
```bash
python index_semantics.py
```

### 3. Running the REST API Server & UI
To spin up the HTTP web server backend:
```bash
python server.py
```
Then navigate to `http://localhost:8000` to try multi-hop queries, visualizer graphs, crawl sync queues, and database diagnostics.

### 4. Technical Documentation
For full API contracts, database schemas, traversal scoring math, and flowcharts, see the [Technical Documentation Suite](docs/README.md).
