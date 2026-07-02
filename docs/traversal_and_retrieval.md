# Graph Traversal & Evidence Retrieval Subsystem

The Traversal and Retrieval Subsystem executes BFS search across the entity-relation knowledge graph, ranks paths, extracts relevant paragraphs, and builds structured reasoning subgraphs.

---

## 1. BFS Traversal & Policy Constraints

The BFS traversal loop is implemented in [traversal_engine.py](file:///home/vicky/v_drive/Codes/Graphyra/traversal_engine.py). It expands outwards from seed entity anchors up to configured policy thresholds:

* **`max_depth`**: Hops limit from seed nodes (default `3`).
* **`max_entities`**: Budget limit for visited nodes to prevent layout slowdowns (default `15`).
* **`min_relevance`**: Pruning threshold score (default `0.2`).
* **`depth_penalty`**: Linear penalty score per hop to favor short paths (default `0.1`).

---

## 2. Dynamic Traversal Scoring Formula

Graphyra evaluates the relevance of a path dynamically at each step of BFS expansion using the following formula:

$$\text{TraversalScore} = (\text{RelationWeight} \times \text{QueryRelevance} \times \text{EvidenceSupport}) - (\text{Depth} \times \text{DepthPenalty})$$

### Scoring Factors:
1. **Relation Weight** ($w_{\text{relation}}$): Looked up from the `relation_weights` configuration map inside [TraversalPolicy](file:///home/vicky/v_drive/Codes/Graphyra/models/traversal_models.py):
   * `"mentions"`: $1.0$
   * `"links_to"`: $0.8$
   * `"contains"`: $0.7$
   * `"similar_to"`: $0.4$
2. **Query Relevance** ($r_{\text{query}}$): Checks matching overlaps between the user's search string and the target entity's name. Exposes a hook to switch from simple keyword overlap ($1.0$ if overlap, else $0.5$) to embedding cosine similarities in the future.
3. **Evidence Support** ($s_{\text{evidence}}$): Computes the number of database text chunks referencing the target anchor:
   $$\text{SupportFactor} = 1.0 + \min\left(1.0, \frac{\text{density\_count}}{5}\right)$$
4. **Depth Penalty** ($d_{\text{penalty}}$): Subtracts points based on the distance from the query start node:
   $$\text{Penalty} = \text{depth} \times \text{policy.depth_penalty}$$

Paths with a final score below `min_relevance` are discarded (pruned), and remaining paths are ordered by `traversal_score` so that the most promising exploration paths are processed first.

---

## 3. Evidence Extraction & Subgraphs

Once traversal completes, the retrieval engine resolves the visited nodes into evidence:

### 3.1 `EvidenceRetriever`
Located in [storage/evidence_retriever.py](file:///home/vicky/v_drive/Codes/Graphyra/storage/evidence_retriever.py), it pulls chunks containing mentions of the visited entities, and wraps them in a list of **`CandidateEvidence` DTOs**:
```python
@dataclass
class CandidateEvidence:
    chunk: Chunk
    best_traversal_score: float
    min_depth: int
    discovered_by: List[str]
    paths: List[TraversalPath]
    bm25_score: Optional[float] = None
    semantic_score: Optional[float] = None
    final_score: Optional[float] = None
```

### 3.2 `SubgraphBuilder`
Located in [subgraph_builder.py](file:///home/vicky/v_drive/Codes/Graphyra/subgraph_builder.py), it compiles the retrieved `CandidateEvidence` list, visited entities, traversed links, and matching paths into a single `ReasoningSubgraph` object. Exposes:
* `extract()`: Creates the subgraph object.
* `prune()`: Dynamically filters out low-scoring nodes and orphan chunk mentions.
* `assemble()`: Serializes the final subgraph into a structured dictionary ready for browser visualization and LLM context prompt generation.
