# Retrieval Pipeline Walkthrough

This document traces the end-to-end execution of a single query through Graphyra's multi-stage retrieval pipeline, showing how raw questions are resolved into explainable, structured context subgraphs for downstream language models.

---

## The Query Life Cycle Diagram

```text
       [ User Question ]
               │
               ▼
   [ Seed Anchor Discovery ] ◄─── Dictionary Lookup & Vector Index Search
               │
               ▼
     [ Candidate Fusion ]    ◄─── De-duplicate and rank initial root seeds
               │
               ▼
    [ Stateful Heap Search ] ◄─── Expand path hops prioritizing using MRV & ECB
               │
               ▼
      [ Evidence Ranking ]   ◄─── Run Lexical (BM25) & Semantic similarity
               │
               ▼
    [ Context Subgraph ]     ◄─── Build graph visualizer + LLM context prompt
```

---

## Step-by-Step Flow

### Step 1: Query Input
The client sends a natural language question to the main coordinator endpoint (e.g., `Graphyra.retrieve("question")` or POST `/api/query`).
- **Example Query**: `"What is the relationship between Entity A and Entity B?"`

### Step 2: Seed Anchor Discovery
Graphyra executes two parallel lookup pipelines to identify the starting points (seeds) of the query:
1. **Dictionary Mention Detection**: normalizes the query text, splits it into search terms, and checks against the preloaded case-insensitive alias index map.
2. **Vector Semantic Search**: Converts the natural language question into a query embedding vector ($\vec{q}$) using the bootstrapped `EmbeddingEngine`, and performs a cosine-similarity search over the SQLite vector index (`embeddings.db`).
   - If semantic matches meet threshold, the extractor pulls the entity anchors referenced by the top chunks.

### Step 3: Candidate Fusion
The `CandidateFusionEngine` merges the starting entities found by the dictionary extractor and the vector search.
- Exact name matches are scaled by `direct_match_weight`.
- Semantic matches are scaled by `semantic_match_weight`.
- Identical anchors are deduplicated, and the final list is sorted to produce a prioritized queue of root seed nodes.

### Step 4: Stateful Heap Search
The `TraversalEngine` delegates search to the stateful `RetrievalEngine` starting from the prioritized query seeds:
- **Budgeting**: Checks global budget boundaries (`entity_budget = 30`, `chunk_budget = 20`) to prevent exploration explosion.
- **Neighbor Evaluation**: The `CandidateGenerator` generates adjacent chunk and entity neighbors.
- **Dynamic Pruning via ECB**: Computes a global **Expansion Context Baseline (ECB)** over the candidate chunks generated at this expansion step. Only chunks passing the dynamic threshold (`MRV - ECB > acceptance_margin`) are accepted.
- **Priority Propagation**: Pushes successor search states onto the Frontier heap, calculating child priorities using momentum alpha ($\alpha$) and expansion beta ($\beta$) weights.

### Step 5: Evidence Ranking
The `EvidenceRanker` executes the selected `RankingStrategy` (e.g., `GraphCentricStrategy`) over the accepted evidence chunks:
- Traversal priority is integrated directly to promote chunks retrieved along structurally high-relevance traversal paths.
- BM25 and Semantic similarity act as precision-based tie-breakers.

### Step 6: Context Subgraph Construction
TheCoordination layers compile the ranked evidence chunks, traversal paths, and entities into a unified `ReasoningSubgraph` payload:
- **ASCII Flowchart**: Formats path hops into a vertical flow diagram.
- **Context Prompt**: Serializes the ranked evidence paragraphs and node relations, producing a structured text payload ready for LLM prompt context injection.
