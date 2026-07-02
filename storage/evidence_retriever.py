from models.traversal_models import TraversalResult
from storage.chunk_repository import ChunkRepository
from storage.mention_repository import MentionRepository


class EvidenceRetriever:

    def __init__(self, storage):
        self.storage = storage
        self.chunk_repo = ChunkRepository(storage)
        self.mention_repo = MentionRepository(storage)

    def retrieve_evidence(self, traversal_result: TraversalResult) -> list:
        """
        Retrieves all CandidateEvidence objects wrapping Chunk objects and 
        traversal metadata for the visited retrieval anchors.
        """
        from models.traversal_models import CandidateEvidence
        
        # 1. Map chunk_id to the list of visited entities that mention it
        chunk_to_entities = {}
        for ent_id in traversal_result.visited_nodes:
            cids = self.mention_repo.get_chunks_for_entity(ent_id)
            for cid in cids:
                if cid not in chunk_to_entities:
                    chunk_to_entities[cid] = []
                if ent_id not in chunk_to_entities[cid]:
                    chunk_to_entities[cid].append(ent_id)
                    
        # 2. Map entity_id to all paths that discovered it
        entity_to_paths = {}
        for path in traversal_result.discovered_paths:
            ent_id = path.target_entity
            if ent_id not in entity_to_paths:
                entity_to_paths[ent_id] = []
            entity_to_paths[ent_id].append(path)

        # 3. Build CandidateEvidence list
        candidate_evidences = []
        for cid, ent_ids in chunk_to_entities.items():
            chunk = self.chunk_repo.get(cid)
            if not chunk:
                continue
                
            # Collect all paths that reached any of the entities discovering this chunk
            paths = []
            for ent_id in ent_ids:
                paths.extend(entity_to_paths.get(ent_id, []))
                
            if not paths:
                best_score = 0.0
                min_depth = 99
            else:
                best_score = max(p.traversal_score for p in paths)
                min_depth = min(p.depth for p in paths)
                
            evidence = CandidateEvidence(
                chunk=chunk,
                best_traversal_score=best_score,
                min_depth=min_depth,
                discovered_by=ent_ids,
                paths=paths
            )
            candidate_evidences.append(evidence)
            
        # Sort candidate evidences by best_traversal_score descending
        candidate_evidences.sort(key=lambda e: e.best_traversal_score, reverse=True)
        return candidate_evidences
