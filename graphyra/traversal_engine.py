from typing import List, Dict, Set
from graphyra.models.traversal_models import (
    TraversalRequest,
    TraversalResult,
    RetrievalResult,
    RetrievalStatistics,
    RetrievalDiagnostics,
    TraversalPath,
    TraversedRelation,
    NodeType
)
from graphyra.storage.graph_repository import GraphRepository
from graphyra.retrieval.traversal.expansion_policy import DefaultExpansionPolicy


class TraversalEngine:

    def __init__(
        self,
        graph_repository: GraphRepository,
        entity_repository,
        mention_repository,
        embedding_engine=None,
        vector_index=None
    ):
        self.graph_repo = graph_repository
        self.entity_repo = entity_repository
        self.mention_repo = mention_repository
        self.embedding_engine = embedding_engine
        self.vector_index = vector_index

    def traverse(self, request: TraversalRequest) -> RetrievalResult:
        """
        Executes the stateful, evidence-driven retrieval process via RetrievalEngine,
        returning a RetrievalResult DTO.
        """
        import time
        start_time = time.time()
        
        from graphyra.storage.chunk_repository import ChunkRepository
        from graphyra.retrieval.retrieval_engine import RetrievalEngine
        
        chunk_repo = ChunkRepository(self.graph_repo.storage)
        retrieval_engine = RetrievalEngine(
            graph_repo=self.graph_repo,
            entity_repo=self.entity_repo,
            mention_repo=self.mention_repo,
            chunk_repo=chunk_repo,
            embedding_engine=self.embedding_engine,
            vector_index=self.vector_index
        )
        
        retrieval_state = retrieval_engine.search(
            query=request.query,
            seed_entities=request.seed_entities,
            policy=request.policy
        )
        
        # Reconstruct unique TraversedRelation objects from the visited paths
        unique_relations = []
        seen_rels = set()
        for path in retrieval_state.discovered_paths:
            for i in range(len(path.hops) - 1):
                u, v = path.hops[i], path.hops[i+1]
                rels = self.graph_repo.get_neighbors(u)
                for r in rels:
                    if (r.source == u and r.target == v) or (r.source == v and r.target == u):
                        key = (r.source, r.target, r.relation_type)
                        if key not in seen_rels:
                            seen_rels.add(key)
                            unique_relations.append(r)
                            
        # Sort paths by score descending
        discovered_paths = sorted(retrieval_state.discovered_paths, key=lambda p: p.traversal_score, reverse=True)
        
        visited_entities = retrieval_state.visited_entities
        visited_chunks = retrieval_state.visited_chunks
        
        policy = request.policy
        elapsed_time_ms = round((time.time() - start_time) * 1000.0, 2)
        
        statistics = RetrievalStatistics(
            entities_visited=len(visited_entities),
            chunks_visited=len(visited_chunks),
            entity_budget_remaining=max(0, policy.entity_budget - len(visited_entities)),
            chunk_budget_remaining=max(0, policy.chunk_budget - len(visited_chunks)),
            elapsed_time_ms=elapsed_time_ms
        )
        
        pruned_states = max(0, retrieval_state.spawned_states_count - retrieval_state.explored_states_count)
        diagnostics = RetrievalDiagnostics(
            explored_states=retrieval_state.explored_states_count,
            accepted_chunks=len(retrieval_state.global_accepted_chunks),
            rejected_chunks=retrieval_state.rejected_chunks_count,
            frontier_expansions=retrieval_state.frontier_expansions_count,
            convergence_reason=retrieval_state.convergence_reason,
            spawned_states=retrieval_state.spawned_states_count,
            pruned_states=pruned_states
        )
        
        return RetrievalResult(
            accepted_evidence=retrieval_state.global_accepted_chunks,
            supporting_entities=retrieval_state.visited_entities_order,
            traversal_paths=discovered_paths,
            evidence_scores=retrieval_state.evidence_scores,
            statistics=statistics,
            diagnostics=diagnostics,
            _legacy_relations=unique_relations,
            _legacy_scores=retrieval_state.scores
        )


