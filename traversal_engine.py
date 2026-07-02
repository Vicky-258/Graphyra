from typing import List, Dict, Set
from models.traversal_models import (
    TraversalRequest,
    TraversalResult,
    TraversalPath,
    TraversedRelation
)
from storage.graph_repository import GraphRepository


class TraversalEngine:

    def __init__(self, graph_repository: GraphRepository, entity_repository, mention_repository):
        self.graph_repo = graph_repository
        self.entity_repo = entity_repository
        self.mention_repo = mention_repository

    def traverse(self, request: TraversalRequest) -> TraversalResult:
        """
        Executes a policy-controlled breadth-first search starting from the seed anchors,
        returning a structured TraversalResult.
        """
        policy = request.policy
        visited_nodes = list(request.seed_entities)
        traversed_relations: List[TraversedRelation] = []
        discovered_paths: List[TraversalPath] = []
        scores: Dict[str, float] = {seed_id: 1.0 for seed_id in request.seed_entities}

        # Initialize BFS queue with (entity_id, path_so_far)
        queue = []
        for seed_id in request.seed_entities:
            path = TraversalPath(
                seed_entity=seed_id,
                target_entity=seed_id,
                hops=[seed_id],
                relations=[],
                depth=0,
                traversal_score=1.0
            )
            queue.append((seed_id, path))
            discovered_paths.append(path)

        while queue:
            curr_id, path = queue.pop(0)

            if path.depth >= policy.max_depth:
                continue

            # Fetch neighbors from the storage-decoupled GraphRepository
            neighbors = self.graph_repo.get_neighbors(curr_id)
            for rel in neighbors:
                # Find target anchor ID
                target_id = rel.target if rel.source == curr_id else rel.source

                # Prevent cycles in the current path
                if target_id in path.hops:
                    continue

                # Stop if entity budget exceeded
                if len(visited_nodes) >= policy.max_entities and target_id not in visited_nodes:
                    continue

                new_depth = path.depth + 1
                
                # Calculate path scoring if enabled
                if policy.enable_scoring:
                    # 1. Relation Weight
                    rel_weight = policy.relation_weights.get(rel.relation_type, 0.8)

                    # 2. Query Relevance (defaults to keyword overlap, extendable to embedding similarity)
                    target_ent = self.entity_repo.get(target_id)
                    target_name = target_ent.canonical_name if target_ent else target_id
                    
                    query_words = set(request.query.lower().split())
                    target_words = set(target_name.lower().split())
                    overlap = query_words & target_words
                    query_relevance = 1.0 if overlap else 0.5

                    # 3. Evidence Support (number of chunks referencing the target anchor)
                    evidence_support = len(self.mention_repo.get_chunks_for_entity(target_id))
                    support_factor = 1.0 + min(1.0, evidence_support / 5.0)

                    # Calculate traversal score
                    traversal_score = (rel_weight * query_relevance * support_factor) - (new_depth * policy.depth_penalty)
                    traversal_score = round(max(0.0, traversal_score), 3)
                else:
                    traversal_score = 1.0

                # Prune if score falls below policy threshold
                if policy.enable_scoring and traversal_score < policy.min_relevance:
                    continue

                # Update visited nodes list & anchor score
                if target_id not in visited_nodes:
                    visited_nodes.append(target_id)
                    scores[target_id] = traversal_score
                else:
                    scores[target_id] = max(scores.get(target_id, 0.0), traversal_score)

                # Keep track of unique traversed relations
                rel_dup = False
                for tr in traversed_relations:
                    if (tr.source == rel.source and tr.target == rel.target and tr.relation_type == rel.relation_type):
                        rel_dup = True
                        break
                if not rel_dup:
                    traversed_relations.append(rel)

                # Append path
                new_path = TraversalPath(
                    seed_entity=path.seed_entity,
                    target_entity=target_id,
                    hops=path.hops + [target_id],
                    relations=path.relations + [rel.relation_type],
                    depth=new_depth,
                    traversal_score=traversal_score
                )
                discovered_paths.append(new_path)

                # Queue the neighbor for further expansion
                queue.append((target_id, new_path))

        # Sort discovered paths by traversal score descending
        discovered_paths.sort(key=lambda p: p.traversal_score, reverse=True)

        return TraversalResult(
            visited_nodes=visited_nodes,
            traversed_relations=traversed_relations,
            discovered_paths=discovered_paths,
            scores=scores,
            metadata={
                "policy_used": {
                    "max_depth": policy.max_depth,
                    "max_entities": policy.max_entities,
                    "min_relevance": policy.min_relevance,
                    "depth_penalty": policy.depth_penalty,
                    "enable_scoring": policy.enable_scoring
                }
            }
        )
