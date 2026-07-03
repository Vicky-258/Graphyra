from typing import List, Dict, Set
from graphyra.models.traversal_models import (
    TraversalRequest,
    TraversalResult,
    TraversalPath,
    TraversedRelation,
    NodeType
)
from graphyra.storage.graph_repository import GraphRepository
from graphyra.retrieval.traversal.expansion_policy import DefaultExpansionPolicy


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

        # Telemetry counts
        entity_expansions = 0
        chunk_expansions = 0
        entity_budget_hits = 0
        chunk_budget_hits = 0
        entity_neighbors_pruned = 0
        chunk_neighbors_pruned = 0
        skipped_degree_count = 0
        skipped_budget_count = 0

        # Cache & frontier telemetry
        total_neighbor_lookups = 0
        neighbor_lookup_cache_hits = 0
        total_type_lookups = 0
        type_lookup_cache_hits = 0
        max_frontier_size = 0
        total_neighbors_discovered = 0

        # Precompute degrees if max_degree_threshold is enabled to avoid database query bottleneck
        degrees = {}
        if policy.max_degree_threshold is not None:
            storage = getattr(self.graph_repo, "storage", None)
            if storage:
                with storage.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT source_id, target_id FROM relations")
                    for src, tgt in cursor.fetchall():
                        degrees[src] = degrees.get(src, 0) + 1
                        degrees[tgt] = degrees.get(tgt, 0) + 1

        # Precompute mentions count to avoid database query bottleneck in BFS loop
        mentions_count = {}
        storage = getattr(self.graph_repo, "storage", None)
        if storage:
            with storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT entity_id, COUNT(chunk_id) FROM entity_mentions GROUP BY entity_id")
                for ent_id, count in cursor.fetchall():
                    mentions_count[ent_id] = count

        # Track visited nodes per seed to enforce per-seed budget
        seed_visited = {seed_id: {seed_id} for seed_id in request.seed_entities}

        # Initialize independent budget trackers
        visited_entities = set()
        visited_chunks = set()
        for seed_id in request.seed_entities:
            total_type_lookups += 1
            if getattr(self.graph_repo, "use_cache", False):
                type_lookup_cache_hits += 1
            stype = self.graph_repo.get_node_type(seed_id)
            if stype == NodeType.ENTITY:
                visited_entities.add(seed_id)
            elif stype == NodeType.CHUNK:
                visited_chunks.add(seed_id)

        # Instantiate expansion policy
        expansion_policy = DefaultExpansionPolicy(
            entity_expansion_limit=policy.entity_expansion_limit,
            chunk_expansion_limit=policy.chunk_expansion_limit,
            graph_repo=self.graph_repo
        )

        while queue:
            max_frontier_size = max(max_frontier_size, len(queue))
            curr_id, path = queue.pop(0)

            total_type_lookups += 1
            if getattr(self.graph_repo, "use_cache", False):
                type_lookup_cache_hits += 1
            node_type = self.graph_repo.get_node_type(curr_id)

            if path.depth >= policy.max_depth:
                continue

            # Enforce expansion-level budget check
            if node_type == NodeType.ENTITY and len(visited_entities) > policy.entity_budget:
                continue
            if node_type == NodeType.CHUNK and len(visited_chunks) > policy.chunk_budget:
                continue

            # Record expansions telemetry
            if node_type == NodeType.ENTITY:
                entity_expansions += 1
            elif node_type == NodeType.CHUNK:
                chunk_expansions += 1

            # Fetch neighbors from the storage-decoupled GraphRepository and filter via ExpansionPolicy
            total_neighbor_lookups += 1
            if getattr(self.graph_repo, "use_cache", False):
                neighbor_lookup_cache_hits += 1

            raw_neighbors = self.graph_repo.get_neighbors(curr_id)
            total_neighbors_discovered += len(raw_neighbors)

            neighbors = expansion_policy.expand(curr_id, raw_neighbors)
            
            pruned_count = len(raw_neighbors) - len(neighbors)
            if pruned_count > 0:
                if node_type == NodeType.ENTITY:
                    chunk_neighbors_pruned += pruned_count
                elif node_type == NodeType.CHUNK:
                    entity_neighbors_pruned += pruned_count
            
            for rel in neighbors:
                # Find target anchor ID
                target_id = rel.target if rel.source == curr_id else rel.source

                # Prevent cycles in the current path
                if target_id in path.hops:
                    continue

                total_type_lookups += 1
                if getattr(self.graph_repo, "use_cache", False):
                    type_lookup_cache_hits += 1
                target_type = self.graph_repo.get_node_type(target_id)

                # 1. Enforce max_degree_threshold
                if policy.max_degree_threshold is not None:
                    target_degree = degrees.get(target_id) if target_id in degrees else len(self.graph_repo.get_neighbors(target_id))
                    if target_degree > policy.max_degree_threshold:
                        skipped_degree_count += 1
                        continue

                # 2. Enforce per_seed_budget
                if policy.per_seed_budget is not None and target_id not in seed_visited[path.seed_entity]:
                    if len(seed_visited[path.seed_entity]) >= policy.per_seed_budget:
                        skipped_budget_count += 1
                        continue

                # 3. Enforce independent budget limits
                if target_type == NodeType.ENTITY:
                    if len(visited_entities) >= policy.entity_budget and target_id not in visited_entities:
                        entity_budget_hits += 1
                        continue
                elif target_type == NodeType.CHUNK:
                    if len(visited_chunks) >= policy.chunk_budget and target_id not in visited_chunks:
                        chunk_budget_hits += 1
                        continue

                # 4. Enforce legacy total_budget / max_entities for compatibility
                if policy.total_budget is not None:
                    if len(visited_nodes) >= policy.total_budget and target_id not in visited_nodes:
                        skipped_budget_count += 1
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
                    evidence_support = mentions_count.get(target_id, 0)
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

                # Track node type in sets
                if target_type == NodeType.ENTITY:
                    visited_entities.add(target_id)
                elif target_type == NodeType.CHUNK:
                    visited_chunks.add(target_id)

                # Update per-seed visited sets
                if target_id not in seed_visited[path.seed_entity]:
                    seed_visited[path.seed_entity].add(target_id)

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

        max_depth_reached = 0
        if discovered_paths:
            max_depth_reached = max(p.depth for p in discovered_paths)

        # Compute cache & frontier aggregates
        total_expansions = entity_expansions + chunk_expansions
        average_branching_factor = total_neighbors_discovered / total_expansions if total_expansions > 0 else 0.0
        
        neighbor_cache_hit_rate = neighbor_lookup_cache_hits / total_neighbor_lookups if total_neighbor_lookups > 0 else 0.0
        type_cache_hit_rate = type_lookup_cache_hits / total_type_lookups if total_type_lookups > 0 else 0.0
        overall_cache_hit_rate = (neighbor_lookup_cache_hits + type_lookup_cache_hits) / (total_neighbor_lookups + total_type_lookups) if (total_neighbor_lookups + total_type_lookups) > 0 else 0.0

        return TraversalResult(
            visited_nodes=visited_nodes,
            traversed_relations=traversed_relations,
            discovered_paths=discovered_paths,
            scores=scores,
            metadata={
                "policy_used": {
                    "max_depth": policy.max_depth,
                    "entity_budget": policy.entity_budget,
                    "chunk_budget": policy.chunk_budget,
                    "entity_expansion_limit": policy.entity_expansion_limit,
                    "chunk_expansion_limit": policy.chunk_expansion_limit,
                    "enable_scoring": policy.enable_scoring
                },
                "traversal_stats": {
                    "nodes_visited": len(visited_nodes),
                    "edges_traversed": len(traversed_relations),
                    "seeds_expanded": len(request.seed_entities),
                    "entities_visited": len(visited_entities),
                    "chunks_visited": len(visited_chunks),
                    "entity_expansions": entity_expansions,
                    "chunk_expansions": chunk_expansions,
                    "traversal_expansions": total_expansions,
                    "entity_budget_hits": entity_budget_hits,
                    "chunk_budget_hits": chunk_budget_hits,
                    "entity_neighbors_pruned": entity_neighbors_pruned,
                    "chunk_neighbors_pruned": chunk_neighbors_pruned,
                    "maximum_depth_reached": max_depth_reached,
                    "max_frontier_size": max_frontier_size,
                    "average_branching_factor": round(average_branching_factor, 2),
                    "neighbor_cache_hit_rate": round(neighbor_cache_hit_rate * 100.0, 1),
                    "type_cache_hit_rate": round(type_cache_hit_rate * 100.0, 1),
                    "overall_cache_hit_rate": round(overall_cache_hit_rate * 100.0, 1)
                }
            }
        )
