# Semantic Search & Candidate Fusion Subsystem

The Semantic Search Subsystem implements parallel semantic candidate discovery, isolated vector index databases, auto-healing rebuilds, and candidate seed fusion.

---

## 1. Subsystem Architecture

The semantic layer is decoupled from Graphyra's core relational database and model classes.

```text
Relational KB (graphyra.db)
        │
        ▼
   [EmbeddingIndexer] <---> [EmbeddingEngine] <---> [EmbeddingProvider] (sentence-transformers)
        │
        ▼
   [SQLiteVectorIndex] (embeddings.db)
```

### Core Interface Roles:
* **`EmbeddingProvider`**: Abstract adapter wrapper.
  * `SentenceTransformerProvider`: Executes the local `all-MiniLM-L6-v2` embedding model.
  * `MockEmbeddingProvider`: Produces deterministic, normalized pseudorandom float arrays based on text hashes, ensuring fast, offline test runs.
* **`EmbeddingEngine`**: Provides stateless vector generation for queries and text chunk lists.
* **`VectorIndex`**: Agnostic of Graphyra schemas. Handles vector insert, persistence, and similarity search over generic `(id, vector)` pairs.
* **`SQLiteVectorIndex`**: Persistent implementation writing vectors to `embeddings.db`. Runs fast in-memory cosine similarity searches on query vector ($\vec{q}$) and cached normalized vectors ($\vec{c}$) using numpy dot-products:
  $$\text{Similarity} = \vec{q} \cdot \vec{c}_i$$

---

## 2. Incremental Syncing & Model-Drift Recovery

The indexing lifecycle is orchestrated by **`EmbeddingIndexer`** inside [semantic/indexer.py](file:///home/vicky/v_drive/Codes/Graphyra/semantic/indexer.py):

* **Incremental Syncing**: During pipeline crawlers, `index_chunks(chunk_list)` is called. It checks the index cached ID set and generates embeddings only for new or modified chunk IDs, avoiding expensive full scans.
* **Model-Drift Verification**: When initialized, `verify_and_rebuild_if_needed()` compares the active model configuration (e.g. `all-MiniLM-L6-v2`) with the model name key stored in the index metadata table. 
* **Self-Healing Rebuild**: If a mismatch is detected (e.g. model changed from `mock` to `all-MiniLM-L6-v2`), it immediately invalidates the index, runs `clear()`, and executes a full scan rebuild (`index_missing_chunks()`).

---

## 3. Candidate Seed Fusion Engine

The query resolver executes keyword matching and semantic search in parallel. Results are fused using the **`CandidateFusionEngine`** inside [semantic/fusion.py](file:///home/vicky/v_drive/Codes/Graphyra/semantic/fusion.py):

* **Direct Entity score**: Direct entity matches are scaled by `direct_match_weight` (default `1.0`).
* **Semantic Entity score**: Semantic chunk matches are mapped to entities and scaled by `semantic_match_weight` (default `0.8`).
* **Fusion Math**: If an entity is discovered by both channels, it selects the maximum score:
  $$S(e) = \max \left( D(e) \cdot w_{\text{direct}}, \max_{c} (Sim(c) \cdot w_{\text{semantic}}) \right)$$
* Deduplicated, ranked traversal seeds are then fed directly into the traversal engine.

---

## 4. Standalone CLI Tool

To run semantic indexing on already stored chunks at any time, run the standalone tool:
```bash
python index_semantics.py
```
This utility initializes the storage connection, bootstraps the semantic layer, checks for model-drift, and incrementally indexes any unindexed chunks.
