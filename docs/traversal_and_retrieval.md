# Stateful Search & Evidence Retrieval Subsystem

The Stateful Search and Retrieval Subsystem executes query-guided priority search across the entity-relation knowledge graph, prunes irrelevant neighbors, extracts relevant paragraphs on the fly, and builds structured reasoning subgraphs.

---

## 1. Stateful Search & Policy Constraints

The stateful search loop is managed by `RetrievalEngine` (defined in [retrieval_engine.py](../graphyra/retrieval/retrieval_engine.py)). It expands outwards from seed entity anchors up to configured policy thresholds:

* **`max_depth`**: Hops limit from seed nodes (default `2`).
* **`entity_budget`**: Global limit for visited entities to prevent exploration explosion (default `30`).
* **`chunk_budget`**: Global limit for visited chunks during search (default `20`).
* **`min_priority_threshold`**: Minimum state priority threshold. Path branches falling below this priority are pruned (default `0.1`).
* **`consecutive_misses_limit`**: Stop traversal if search loops for $N$ steps without discovering new accepted chunks (default `5`).

---

## 2. Priority Propagation Formula

Graphyra evaluates the relevance of search states dynamically. The priority of a successor state ($S_{\text{child}}$) is propagated from its parent state using momentum decay weighting:

$$P_{\text{child}} = \alpha \cdot P_{\text{parent}} + (1 - \alpha) \cdot \left( \beta \cdot \text{MRV} + (1 - \beta) \cdot \text{EP} \right)$$

### Parameters & Scoring Factors:
1. **Momentum Alpha** ($\alpha$, default `0.7`): Decay factor scaling the weight of the parent's historical priority.
2. **Expansion Beta** ($\beta$, default `0.2`): Balance weight between immediate relevance (MRV) and exploration potential (EP).
3. **Multi-hop Relevance Value (MRV)**: A weighted combination of Query Alignment (QA), Context Continuity (CC), Novelty (NV), and Expansion Potential (EP) scores:
   $$\text{MRV} = w_{\text{qa}} \cdot \text{QA} + w_{\text{cc}} \cdot \text{CC} + w_{\text{nv}} \cdot \text{NV} + w_{\text{ep}} \cdot \text{EP}$$
4. **Expansion Potential (EP)**: Score representing how many new, unvisited entities are mentioned in the candidate chunk.

---

## 3. Expansion Context Baseline (ECB) Filtering

To avoid budget saturation by irrelevant or long-tail connections (such as entities mentioned in only a single chunk), the engine performs a global evaluation over all candidate chunks at each expansion step:
1. **Global Candidate Gathering:** Accumulates all chunks across all adjacent target entities.
2. **ECB Calculation:** Computes the average MRV of the candidate set:
   $$\text{ECB} = \frac{1}{|C|} \sum_{c \in C} \text{MRV}(c)$$
3. **Marginal Gain Thresholding:** Only chunks satisfying the threshold are accepted as evidence and allowed to spawn successor states:
   $$\text{MRV} - \text{ECB} > \text{acceptance\_margin}$$

---

## 4. Retrieval Result Data Transfer Object

The coordinator `Graphyra.retrieve()` returns a structured DTO representing the retrieval outcome:

```python
@dataclass
class RetrievalResult:
    accepted_evidence: List[Chunk]       # Final evidence chunks selected
    supporting_entities: List[str]      # Unique entities visited along the paths
    traversal_paths: List[TraversalPath] # Path hops and relations traversed
    evidence_scores: List[EvidenceScore] # Detailed priority and marginal gain metrics
    statistics: RetrievalStatistics     # Execution counters (budget remaining, latency)
    diagnostics: RetrievalDiagnostics   # Search loop details (spawned/explored/pruned states)
```
