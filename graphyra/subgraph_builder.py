from graphyra.models.traversal_models import ReasoningSubgraph, TraversalResult, TraversedRelation, TraversalPath
from graphyra.models.chunk import Chunk


class SubgraphBuilder:

    def __init__(self, storage):
        self.storage = storage

    def extract(self, traversal_result: TraversalResult, chunks: list[Chunk]) -> ReasoningSubgraph:
        """
        Extracts a ReasoningSubgraph container grouping anchors, relationships, chunks, and paths.
        """
        return ReasoningSubgraph(
            entities=traversal_result.visited_nodes,
            relations=traversal_result.traversed_relations,
            chunks=chunks,
            paths=traversal_result.discovered_paths
        )

    def prune(self, subgraph: ReasoningSubgraph, min_score: float) -> ReasoningSubgraph:
        """
        Prunes the subgraph by filtering out anchors, paths, relations, and chunks
        that fall below the minimum score threshold.
        """
        # 1. Filter paths
        pruned_paths = [p for p in subgraph.paths if p.score >= min_score]

        # 2. Identify allowed entities (seed entities can bypass pruning since they are seeds)
        # However, it's safer to keep any entity that is part of a kept path
        allowed_entities = set()
        for p in pruned_paths:
            allowed_entities.update(p.hops)

        # 3. Filter relations to keep only those connecting allowed entities
        pruned_relations = []
        for rel in subgraph.relations:
            if rel.source in allowed_entities and rel.target in allowed_entities:
                pruned_relations.append(rel)

        # 4. Filter chunks to keep only those that mention any of the allowed entities
        # We check mentions via storage/database or metadata mapping
        from graphyra.storage.mention_repository import MentionRepository
        mention_repo = MentionRepository(self.storage)
        
        pruned_chunks = []
        for chunk in subgraph.chunks:
            # Get entities mentioned in this chunk
            mentions = mention_repo.get_entities_for_chunk(chunk.id)
            if any(ent_id in allowed_entities for ent_id in mentions):
                pruned_chunks.append(chunk)

        return ReasoningSubgraph(
            entities=list(allowed_entities),
            relations=pruned_relations,
            chunks=pruned_chunks,
            paths=pruned_paths
        )

    def assemble(self, subgraph: ReasoningSubgraph) -> dict:
        """
        Formats the ReasoningSubgraph into a query-context-ready dictionary.
        """
        formatted_paths = []
        for path in subgraph.paths:
            formatted_paths.append({
                "seed": path.seed_entity,
                "target": path.target_entity,
                "hops": path.hops,
                "relations": path.relations,
                "score": path.score,
                "depth": path.depth
            })

        formatted_chunks = []
        for chunk in subgraph.chunks:
            formatted_chunks.append({
                "id": chunk.id,
                "artifact_id": chunk.artifact_id,
                "content": chunk.content,
                "metadata": chunk.metadata
            })

        return {
            "entities": subgraph.entities,
            "relations": [
                {
                    "source": r.source,
                    "target": r.target,
                    "relation_type": r.relation_type,
                    "score": r.score
                }
                for r in subgraph.relations
            ],
            "chunks": formatted_chunks,
            "paths": formatted_paths
        }
