# Graphyra Ecosystem Architecture & Modularization Guide

This document describes the modular architecture of the Graphyra ecosystem. The codebase is split into four distinct repositories, isolating the **Graphyra Core** library from data adapters, applications, and evaluation frameworks.

---

## Ecosystem Diagram

```text
                    Graphyra Core
                         ▲
        ┌────────────────┼────────────────┐
        │                │                │
        │                │                │
   Graphyra-        Graphyra-      Graphyra-
   Adapters         Wrappers       Evaluation
```

---

## 1. Graphyra Core (this repository)

### Responsibility
The core framework, storage layers, and algorithms.

### Invariants
* **No UI:** Contains no HTML/CSS, React code, or user assets.
* **No Web Server:** Contains no REST server, WSGI/ASGI launchers, or HTTP listening endpoints.
* **No Evaluation:** Contains no benchmarks, experiments runner, or profiling metrics (other than runtime telemetry hooks).
* **No Domain-Specific Logic:** Imparts no knowledge about specific datasets (like Genshin Impact).

### Layout
```text
Graphyra/
    graphyra/
        ingestion/       # Ingestion parsing framework
        interfaces/      # contracts & Base adapter interfaces
        models/          # Core model dataclasses & NodeType enums
        retrieval/       # Retrieval controllers & ranking strategies
        storage/         # SQLite repositories
        utils/           # Graph assembly utilities
    tests/               # Core framework unit tests
    docs/                # Architecture docs
    pyproject.toml       # Core build/dependency settings
```

---

## 2. Graphyra Adapters

### Responsibility
Plugs that parse domain-specific external sources (e.g. MediaWiki, PDFs, markdown files) and ingest them via the Core framework.

### Example: `graphyra-adapter-genshin`
* Located alongside Graphyra in `Codes/Graphyra-Lib/graphyra-adapter-genshin`.
* Responsible for crawling the Genshin Wiki, parsing pages, and feeding normalized `ContentBlock` entries to the Core ingestion pipeline.
* **Invariant:** Contains no custom traversal or retrieval code.

---

## 3. Graphyra Wrappers

### Responsibility
User-facing applications and APIs that expose Graphyra retrieval to users.

* Located at `Codes/Graphyra-Lib/Graphyra-Wrappers`.
* Contains:
  * `server.py`: Raw HTTP REST API.
  * `frontend/` & `web/`: Explorer React dashboard.
  * `query.py` & `trace_query.py`: Developer CLI tools.
* **Invariant:** Consumes Graphyra Core as a library; contains no custom retrieval or ranking algorithms.

---

## 4. Graphyra Evaluation

### Responsibility
Benchmarking, profiling, and regression test suites for measuring quality and latency.

* Located at `Codes/Graphyra-Lib/Graphyra-Evaluation`.
* Contains:
  * `evaluation/run_traversal_experiments.py`: Benchmark experiments.
  * `evaluation/run_scale_evaluation.py`: Scaling and profiling scripts.
  * `graphyra.db` & `embeddings.db`: Datasets for validation.
* **Invariant:** A pure developer utility; never a runtime dependency of Graphyra Core.
