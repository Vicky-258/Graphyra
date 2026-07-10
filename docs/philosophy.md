# Graphyra Philosophy

Graphyra is not just another Retrieval-Augmented Generation (RAG) backend. It is an **entity-centric, graph-guided evidence retrieval engine**. It is built on a specific set of architectural values and design principles that differentiate it from vector-only or unstructured text search backends.

---

## The Core Pillars

### 1. Graphs Before Vectors
Most search engines treat documents as bags of words or vectors. Graphyra treats knowledge as a network of **Entities** (conceptual anchors) and **Artifacts** (physical documents) connected by structural relations. 
By placing graph structure first, Graphyra can navigate interconnected topics, trace dependencies, and discover context that is semantic, relational, and structured rather than purely numeric.

### 2. Explicit Relations Over Implicit Similarity
Vector embeddings are powerful but fuzzy. They capture implicit topic similarity (e.g. "EntityA is similar to EntityB") but lose the specific nature of the connection. 
Graphyra prioritizes **explicit relationships** (e.g. `successor_of`, `links_to`, `member_of`) defined in a directed graph. This allows retrieval traversal to navigate concrete paths instead of calculating high-dimensional distances.

### 3. Retrieval First, Generative Optional
Graphyra is a **retrieval engine**, not a reasoning engine. Its task is to locate, extract, rank, and summarize the best possible candidate evidence from a complex corpus and present it as a clean, structured context. 
What happens downstream is independent of Core: whether the output goes into a visualizer dashboard, a local classification model, or a large language model (LLM), Graphyra remains completely decoupled.

### 4. Explainability as a Core Invariant
Traditional vector databases are black boxes: they return a list of document chunks and a float score, but cannot explain *why* a document was selected.
Graphyra's traversals are fully explainable. Every retrieved evidence chunk is associated with the exact path hops, seed entities, and relation types traversed to discover it. This guarantees auditability and allows developers and end-users to trace the origin of every piece of retrieved context.

### 5. Domain Agnosticism
Graphyra Core makes zero assumptions about the source material. It contains no concepts of games, wikis, laws, medical records, or codebases.
Adapters handle the mapping of external domains into generic `KnowledgeDocument` containers. The core library only understands generic graph structures (Artifacts, Entities, Chunks, and Relations) and processes them deterministically.

---

## Why Graphyra?

| Aspect | Traditional Vector Search (RAG) | Graphyra |
| :--- | :--- | :--- |
| **Logic** | Implicit vector similarity | Explicit traversal paths |
| **Explanation** | Score value only | Full path trace of seed -> hop -> target |
| **Multi-Hop** | Poor (requires complex query expansion) | Native (explores graph neighbors recursively) |
| **Decoupling** | Tied to vector model dimension | decoupled storage, plugin-friendly model provider |
| **Accuracy** | Prone to noise drift | Highly precise, bounded by structured relations |
