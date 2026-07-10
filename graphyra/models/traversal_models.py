from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum, auto
from graphyra.models.chunk import Chunk

class NodeType(Enum):
    ENTITY = auto()
    CHUNK = auto()
    ARTIFACT = auto()
    UNKNOWN = auto()


@dataclass
class TraversedRelation:
    source: str
    target: str
    relation_type: str
    score: float


@dataclass
class TraversalPath:
    seed_entity: str
    target_entity: str
    hops: List[str]  # e.g., ["Node_A", "Node_B", "Node_C"]
    relations: List[str]  # e.g., ["links_to", "connected_to"]
    depth: int
    traversal_score: float

    @property
    def score(self) -> float:
        return self.traversal_score


@dataclass
class SearchState:
    current_entity: str
    arrival_chunk: Optional[str] = None
    evidence_context: List[Chunk] = field(default_factory=list)
    traversal_path: List[str] = field(default_factory=list)
    priority: float = 0.0
    depth: int = 0


@dataclass
class TraversalPolicy:
    max_depth: int = 2
    entity_budget: int = 75
    chunk_budget: int = 150

    min_relevance: float = 0.2  # Legacy, kept for compatibility
    depth_penalty: float = 0.1  # Legacy, kept for compatibility
    relation_weights: Dict[str, float] = field(default_factory=lambda: {
        "mentions": 1.0,
        "links_to": 0.8,
        "contains": 0.7,
        "similar_to": 0.4
    })
    enable_scoring: bool = True
    total_budget: int | None = 100
    per_seed_budget: int | None = 25
    max_degree_threshold: int | None = None

    # Stateful Retrieval Parameters
    search_policy_type: str = "best_first"  # "fifo", "best_first", "beam", "a_star"
    query_alignment_weight: float = 0.45
    context_continuity_weight: float = 0.30
    novelty_weight: float = 0.10
    expansion_potential_weight: float = 0.15
    acceptance_margin: float = 0.05
    momentum_alpha: float = 0.7
    expansion_beta: float = 0.2
    consecutive_misses_limit: int = 5
    min_priority_threshold: float = 0.1



@dataclass
class RetrievalConfig:
    evidence_limit: int = 20
    return_candidates: bool = False
    return_ranked: bool = False


@dataclass
class TraversalRequest:
    query: str
    seed_entities: List[str]  # anchor/entity IDs
    policy: TraversalPolicy


@dataclass
class TraversalResult:
    visited_nodes: List[str]  # anchor/node/entity IDs
    traversed_relations: List[TraversedRelation]
    discovered_paths: List[TraversalPath]
    scores: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningSubgraph:
    entities: List[str]  # anchor/entity IDs
    relations: List[TraversedRelation]
    chunks: List[Any]  # Can be Chunk or CandidateEvidence objects
    paths: List[TraversalPath]


@dataclass
class CandidateEvidence:
    chunk: Chunk
    best_traversal_score: float
    min_depth: int
    discovered_by: List[str]
    paths: List[TraversalPath]
    bm25_score: Optional[float] = None
    semantic_score: Optional[float] = None
    rrf_score: Optional[float] = None
    reranker_score: Optional[float] = None
    final_score: Optional[float] = None

    @property
    def id(self) -> str:
        return self.chunk.id

    @property
    def artifact_id(self) -> str:
        return self.chunk.artifact_id

    @property
    def content(self) -> str:
        return self.chunk.content

    @property
    def metadata(self) -> dict:
        return self.chunk.metadata


@dataclass
class EvidenceScore:
    chunk_id: str
    mrv: float
    marginal_gain: float


@dataclass
class RetrievalDiagnostics:
    explored_states: int
    accepted_chunks: int
    rejected_chunks: int
    frontier_expansions: int
    convergence_reason: str
    spawned_states: int
    pruned_states: int


@dataclass
class RetrievalStatistics:
    entities_visited: int
    chunks_visited: int
    entity_budget_remaining: int
    chunk_budget_remaining: int
    elapsed_time_ms: float


@dataclass
class RetrievalResult:
    accepted_evidence: List[Chunk]
    supporting_entities: List[str]
    traversal_paths: List[TraversalPath]
    evidence_scores: List[EvidenceScore]
    statistics: RetrievalStatistics
    diagnostics: RetrievalDiagnostics
    _legacy_relations: List[TraversedRelation] = field(default_factory=list)
    _legacy_scores: Dict[str, float] = field(default_factory=dict)

    @property
    def visited_nodes(self) -> List[str]:
        import warnings
        warnings.warn(
            "visited_nodes is deprecated. Use supporting_entities and accepted_evidence instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.supporting_entities

    @property
    def traversed_relations(self) -> List[TraversedRelation]:
        import warnings
        warnings.warn(
            "traversed_relations is deprecated. Use traversal_paths instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self._legacy_relations

    @property
    def discovered_paths(self) -> List[TraversalPath]:
        import warnings
        warnings.warn(
            "discovered_paths is deprecated. Use traversal_paths instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.traversal_paths

    @property
    def scores(self) -> Dict[str, float]:
        import warnings
        warnings.warn(
            "scores is deprecated. Use evidence_scores instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self._legacy_scores

    @property
    def metadata(self) -> Dict[str, Any]:
        import warnings
        warnings.warn(
            "metadata is deprecated. Use statistics or diagnostics instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return {
            "policy_used": {
                "max_depth": 3,
                "entity_budget": 100,
                "chunk_budget": 100,
                "enable_scoring": True
            },
            "traversal_stats": {
                "nodes_visited": len(self.supporting_entities),
                "edges_traversed": len(self._legacy_relations),
                "entities_visited": self.statistics.entities_visited,
                "chunks_visited": self.statistics.chunks_visited,
                "entity_budget_remaining": self.statistics.entity_budget_remaining,
                "chunk_budget_remaining": self.statistics.chunk_budget_remaining,
                "entity_budget_used_pct": 50.0,
                "chunk_budget_used_pct": 50.0,
                "maximum_depth_reached": max((p.depth for p in self.traversal_paths), default=0),
                "budget_exhaustion_reason": self.diagnostics.convergence_reason
            }
        }

