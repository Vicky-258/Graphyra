from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from models.chunk import Chunk


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
    hops: List[str]  # e.g., ["Nahida", "Rukkhadevata", "Irminsul"]
    relations: List[str]  # e.g., ["successor_of", "connected_to"]
    depth: int
    traversal_score: float

    @property
    def score(self) -> float:
        return self.traversal_score


@dataclass
class TraversalPolicy:
    max_depth: int = 3
    max_entities: int = 15
    min_relevance: float = 0.2
    depth_penalty: float = 0.1
    relation_weights: Dict[str, float] = field(default_factory=lambda: {
        "mentions": 1.0,
        "links_to": 0.8,
        "contains": 0.7,
        "similar_to": 0.4
    })
    enable_scoring: bool = True


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
