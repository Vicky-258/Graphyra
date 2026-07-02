# Graphyra

> **An entity-centric, graph-guided evidence retrieval engine that separates knowledge storage from graph navigation, enabling explainable multi-hop retrieval through structured traversal and evidence ranking.**

---

Graphyra is a graph-guided evidence retrieval engine designed for complex knowledge bases. Instead of retrieving isolated text chunks through vector similarity alone, Graphyra navigates structured relationships between entities, discovers connected evidence through graph traversal, and ranks supporting evidence before it reaches a downstream reasoning system.

---

## 💡 Philosophy

Graphyra is built around three core architectural tenets:

1. **Knowledge lives in documents.** Text paragraphs and segments are the primary sources of truth, context, and semantic nuance.
2. **The graph is not the knowledge.** The graph exists purely as a structural navigation layer designed to guide traversal paths.
3. **Traversal guides evidence discovery.** The relationships between entities provide the roads, while the documents provide the destination.

---

## 🛣️ The Retrieval Pipeline

Graphyra separates query resolution from downstream generation, ensuring that reasoning systems receive a pre-structured, scored, and contextualized evidence subgraph.

```text
       Query (User Search)
                │
                ▼
      [ Entity Resolution ]  <─── Maps aliases/synonyms to canonical anchors
                │
                ▼
       [ Graph Traversal ]   <─── BFS path-scoring over relations
                │
                ▼
     [ Candidate Evidence ]  <─── Groups paragraph chunks along paths
                │
                ▼
      [ Evidence Ranking ]   <─── Ranks chunks by path & semantic scores
                │
                ▼
      [ Context Assembly ]   <─── Builds unified evidence subgraphs
                │
                ▼
       Downstream Reasoning  <─── LLM or downstream consumer (optional)
```

---

## ⭐ Core Capabilities

* **Entity Resolution** — Dynamically resolves aliases, synonyms, and redirect terms to stable retrieval anchors, preventing fragmented paths.
* **Graph Traversal** — Explores connected entities using policy-controlled, weighted BFS paths to discover multi-hop relationships.
* **Evidence Ranking** — Combines traversal scores, query relevance, and evidence support to rank and filter candidate evidence.
* **Incremental Ingestion** — Incrementally registers new artifacts, chunks, entities, and relations without needing to rebuild the entire knowledge base.
* **Explainable Retrieval** — Every chunk of retrieved evidence can be traced back through its traversal path, hops, and source document, offering auditability.

---

## 🏗️ System Architecture

Graphyra is designed as a modular, backend-agnostic system. While it is currently configured with a default stack, each block remains replaceable:

* **Core Engine**: Orchestrates retrieval and handles BFS graph traversals.
* **Storage Providers**: Decoupled from specific databases. Currently implemented using a thread-safe SQLite storage proxy mapping page databases.
* **Vector Indexing**: Decoupled vector interface. Currently implemented using a standalone SQLite index database and a local Sentence Transformers embedding provider.
* **Extractor Adapters**: Interfaces to crawler APIs. Currently configured for MediaWiki page-diff synchronization.
* **Visualizer UI**: Matte dark query trace visualizer and diagnostics statistics dashboard.

---

## 🛠️ Getting Started

### 1. Database Seeding & CLI Trace
To seed the database with the Sumeru lore corpus and run a CLI traversal reasoning trace:
```bash
python main.py
```

### 2. Standalone Semantic Indexing
To generate real embeddings for all stored chunks using the active Sentence Transformer configuration:
```bash
python index_semantics.py
```

### 3. Running the REST API Server & UI
To start the local web backend server:
```bash
python server.py
```
Open `http://localhost:8000` to interact with the query trace storyboard, graph visualizers, and synchronization queues.

### 4. Technical Documentation
For complete API contracts, relational schemas, scoring formulas, and directory flows, check the [Technical Documentation Suite](docs/README.md).
