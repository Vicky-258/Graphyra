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

## 🎯 Suitability Profile

Graphyra is designed for **interconnected knowledge** rather than isolated documents. Its retrieval model assumes that meaningful relationships exist—or can be extracted—between entities, documents, or other knowledge artifacts. The richer this reference structure, the more effectively Graphyra can perform multi-hop evidence discovery and explainable retrieval.

### Good Fit
* **Wikis & Knowledge Bases** (e.g. MediaWiki, internal wikis) where pages explicitly link conceptually.
* **Technical Manuals & Software Docs** where APIs, classes, and specifications cross-reference.
* **Academic & Research Literature** connected through citation trees and bibliography lists.
* **Ontology-Driven Databases** structured around taxonomic relationships.

### Less Suitable
* **Random Chat Logs** or stream transcripts lacking conceptual connections.
* **Independent Blog Posts** or daily news feeds with minimal reference linking.
* **Flat Lists of Files** containing disjointed or isolated facts.

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

## 🏗️ Modular Ecosystem Layout

Graphyra is organized as a modular suite of companion projects grouped under the `Graphyra-Lib/` umbrella directory:

* **[Graphyra Core](docs/ECOSYSTEM.md)** (this repository): Contains the core search algorithms, BFS traversal policies, relational storage repositories, and semantic indexing engines.
* **`Graphyra-Wrappers`**: Contains the REST API server (`server.py`), developer CLI tools (`query.py`, `trace_query.py`), and the interactive search trace dashboard UI.
* **`Graphyra-Evaluation`**: Contains the regression testing suites, scaling benchmarks, traversal profiling scripts, and evaluation baseline metrics.
* **`graphyra-adapter-genshin`**: Contains the crawler, HTML page parser, and exporter adapters connecting external wiki data sources to the Core ingestion pipeline.

---

## 🛠️ Getting Started (Core Library)

### 1. Installation & Environment Setup
Graphyra Core uses `uv` for python environment and dependency resolution.

Initialize the virtual environment:
```bash
uv venv
```

Install standard dependencies:
```bash
uv pip install -e .
```

### 2. Running Core Unit Tests
Execute the pytest suite to verify retrieval engine sanity:
```bash
PYTHONPATH=. uv run pytest
```

### 3. Launching Server, CLI, & Benchmarks
To run user-facing apps or run benchmark metrics, switch to the sibling wrapper and evaluation directories:

* **Start the REST Server & UI Dashboard** (in `Graphyra-Wrappers/`):
  ```bash
  PYTHONPATH=../Graphyra ../Graphyra/.venv/bin/python server.py
  ```
* **Run a Traversal Query Trace CLI** (in `Graphyra-Wrappers/`):
  ```bash
  PYTHONPATH=../Graphyra ../Graphyra/.venv/bin/python trace_query.py "Who is Venti?"
  ```
* **Run Traversal Engine Benchmarks** (in `Graphyra-Evaluation/`):
  ```bash
  PYTHONPATH=../Graphyra ../Graphyra/.venv/bin/python evaluation/run_traversal_experiments.py
  ```

---

## 📖 Documentation Suite

* [Ecosystem & Project Boundary Design Guide](docs/ECOSYSTEM.md)
* [Search & Traversal Pipeline Architecture Reference](architecture.md)
* [Relational Storage Schemas & Repository Pattern](docs/storage.md)
* [Document Ingestion, Chunking, & Mention Extraction](docs/ingestion.md)

