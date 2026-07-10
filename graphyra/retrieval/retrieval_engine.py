import re
import time
import heapq
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Tuple
from graphyra.models.traversal_models import SearchState, NodeType, TraversalPath, EvidenceScore
from graphyra.models.chunk import Chunk


def text_jaccard_similarity(text1: str, text2: str) -> float:
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / len(words1 | words2)


def get_chunk_embedding(chunk, embedding_engine, vector_index) -> Optional[List[float]]:
    if vector_index and hasattr(vector_index, "ids") and hasattr(vector_index, "vectors") and vector_index.vectors is not None:
        if not hasattr(vector_index, "_id_map"):
            vector_index._id_map = {cid: idx for idx, cid in enumerate(vector_index.ids)}
        idx = vector_index._id_map.get(chunk.id)
        if idx is not None:
            return vector_index.vectors[idx]
    if embedding_engine:
        if hasattr(embedding_engine, "provider") and embedding_engine.provider:
            return embedding_engine.provider.embed_text(chunk.content)
        elif hasattr(embedding_engine, "get_query_embedding"):
            return embedding_engine.get_query_embedding(chunk.content)
    return None


def cosine_similarity(v1, v2) -> float:
    arr1 = np.array(v1, dtype=np.float32)
    arr2 = np.array(v2, dtype=np.float32)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))


# ----------------------------------------------------
# Decomposed Scorers and Novelty Provider Interface
# ----------------------------------------------------

class QueryAlignmentScorer:
    def __init__(self, embedding_engine=None, vector_index=None):
        self.embedding_engine = embedding_engine
        self.vector_index = vector_index

    def score(self, query: str, query_embedding: Optional[List[float]], chunk: Chunk) -> float:
        if self.embedding_engine and query_embedding is not None:
            chunk_emb = get_chunk_embedding(chunk, self.embedding_engine, self.vector_index)
            if chunk_emb is not None:
                return cosine_similarity(query_embedding, chunk_emb)
        return text_jaccard_similarity(query, chunk.content)


class ContextContinuityScorer:
    def __init__(self, embedding_engine=None, vector_index=None):
        self.embedding_engine = embedding_engine
        self.vector_index = vector_index

    def score(self, chunk: Chunk, evidence_context: List[Chunk]) -> float:
        if not evidence_context:
            return 0.0
        
        if self.embedding_engine:
            chunk_emb = get_chunk_embedding(chunk, self.embedding_engine, self.vector_index)
            if chunk_emb is not None:
                max_sim = 0.0
                for e_chunk in evidence_context:
                    e_emb = get_chunk_embedding(e_chunk, self.embedding_engine, self.vector_index)
                    if e_emb is not None:
                        sim = cosine_similarity(chunk_emb, e_emb)
                        if sim > max_sim:
                            max_sim = sim
                return max_sim

        max_jac = 0.0
        for e_chunk in evidence_context:
            jac = text_jaccard_similarity(chunk.content, e_chunk.content)
            if jac > max_jac:
                max_jac = jac
        return max_jac


class NoveltyProvider(ABC):
    @abstractmethod
    def score(self, chunk: Chunk, evidence_context: List[Chunk]) -> float:
        pass


class LexicalNoveltyProvider(NoveltyProvider):
    def score(self, chunk: Chunk, evidence_context: List[Chunk]) -> float:
        if not evidence_context:
            return 1.0
        
        words_c = set(re.findall(r'\w+', chunk.content.lower()))
        if not words_c:
            return 0.0
            
        words_ctx = set()
        for e_chunk in evidence_context:
            words_ctx.update(re.findall(r'\w+', e_chunk.content.lower()))
            
        overlap = words_c & words_ctx
        return 1.0 - (len(overlap) / len(words_c))


class ExpansionPotentialScorer:
    def __init__(self, mention_repo, visited_entities: set):
        self.mention_repo = mention_repo
        self.visited_entities = visited_entities

    def score(self, chunk: Chunk) -> float:
        entities = self.mention_repo.get_entities_for_chunk(chunk.id)
        new_entities = [e for e in entities if e not in self.visited_entities]
        if not new_entities:
            return 0.0
        return min(1.0, len(new_entities) / 5.0)


class MRVCombiner:
    def __init__(self, qw: float, cw: float, nw: float, ew: float):
        self.qw = qw
        self.cw = cw
        self.nw = nw
        self.ew = ew

    def combine(self, qa: float, cc: float, nv: float, ep: float) -> float:
        return (self.qw * qa) + (self.cw * cc) + (self.nw * nv) + (self.ew * ep)


# ----------------------------------------------------
# Pluggable Search Policies
# ----------------------------------------------------

class SearchPolicy(ABC):
    @abstractmethod
    def push(self, state: SearchState):
        pass

    @abstractmethod
    def pop(self) -> SearchState:
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        pass


class FIFOSearchPolicy(SearchPolicy):
    def __init__(self):
        self.queue = []

    def push(self, state: SearchState):
        self.queue.append(state)

    def pop(self) -> SearchState:
        return self.queue.pop(0)

    def is_empty(self) -> bool:
        return len(self.queue) == 0


class BestFirstSearchPolicy(SearchPolicy):
    def __init__(self, alpha: float = 0.7, beta: float = 0.2):
        self.heap = []
        self.counter = 0  # Tie-breaker for stable heap sorting
        self.alpha = alpha
        self.beta = beta

    def calculate_priority(self, parent_priority: float, immediate_mrv: float, ep: float) -> float:
        return (self.alpha * parent_priority) + (1.0 - self.alpha) * (self.beta * immediate_mrv + (1.0 - self.beta) * ep)

    def push(self, state: SearchState):
        heapq.heappush(self.heap, (-state.priority, self.counter, state))
        self.counter += 1

    def pop(self) -> SearchState:
        _, _, state = heapq.heappop(self.heap)
        return state

    def is_empty(self) -> bool:
        return len(self.heap) == 0


# ----------------------------------------------------
# Candidate Generator and Evidence Evaluator
# ----------------------------------------------------

class CandidateGenerator:
    def __init__(self, graph_repo, mention_repo, chunk_repo):
        self.graph_repo = graph_repo
        self.mention_repo = mention_repo
        self.chunk_repo = chunk_repo

    def generate_candidates(self, search_state: SearchState) -> List[Tuple[str, List[Chunk]]]:
        curr_entity = search_state.current_entity
        candidate_map = {}
        
        # 1. Bipartite entity-chunk-entity traversal (via mentions)
        curr_chunk_ids = self.mention_repo.get_chunks_for_entity(curr_entity)
        for cid in curr_chunk_ids:
            chk = self.chunk_repo.get(cid)
            if not chk:
                continue
            mentioned_entities = self.mention_repo.get_entities_for_chunk(cid)
            for neighbor_id in mentioned_entities:
                if neighbor_id == curr_entity or neighbor_id in search_state.traversal_path:
                    continue
                if neighbor_id not in candidate_map:
                    candidate_map[neighbor_id] = []
                if chk not in candidate_map[neighbor_id]:
                    candidate_map[neighbor_id].append(chk)
                    
        # 2. Direct entity-to-entity relationships fallback
        relations = self.graph_repo.get_neighbors(curr_entity)
        for rel in relations:
            neighbor_id = rel.target if rel.source == curr_entity else rel.source
            if neighbor_id == curr_entity or neighbor_id in search_state.traversal_path:
                continue
            if neighbor_id.startswith("ENT_"):
                chunk_ids = self.mention_repo.get_chunks_for_entity(neighbor_id)
                for cid in chunk_ids:
                    chk = self.chunk_repo.get(cid)
                    if chk:
                        if neighbor_id not in candidate_map:
                            candidate_map[neighbor_id] = []
                        if chk not in candidate_map[neighbor_id]:
                            candidate_map[neighbor_id].append(chk)
                            
        return list(candidate_map.items())


class EvidenceEvaluator:
    def __init__(self, qa_scorer, cc_scorer, novelty_provider, ep_scorer, mrv_combiner, acceptance_margin: float):
        self.qa_scorer = qa_scorer
        self.cc_scorer = cc_scorer
        self.novelty_provider = novelty_provider
        self.ep_scorer = ep_scorer
        self.mrv_combiner = mrv_combiner
        self.acceptance_margin = acceptance_margin

    def evaluate_candidates(
        self,
        query: str,
        query_embedding: Optional[List[float]],
        search_state: SearchState,
        candidate_chunks: List[Chunk],
        enable_scoring: bool = True
    ) -> List[Tuple[Chunk, float, float, bool]]:
        if not candidate_chunks:
            return []

        if not enable_scoring:
            # Bypass scoring: accept all, flat priority/marginal gain
            return [(chunk, 1.0, 1.0, True) for chunk in candidate_chunks]

        mrv_scores = []
        for chunk in candidate_chunks:
            qa = self.qa_scorer.score(query, query_embedding, chunk)
            cc = self.cc_scorer.score(chunk, search_state.evidence_context)
            nv = self.novelty_provider.score(chunk, search_state.evidence_context)
            ep = self.ep_scorer.score(chunk)
            mrv = self.mrv_combiner.combine(qa, cc, nv, ep)
            mrv_scores.append((chunk, mrv))

        ecb = sum(mrv for _, mrv in mrv_scores) / len(mrv_scores) if len(mrv_scores) > 1 else 0.0

        results = []
        for chunk, mrv in mrv_scores:
            marginal_gain = mrv - ecb
            accepted = marginal_gain > self.acceptance_margin
            results.append((chunk, mrv, marginal_gain, accepted))
        return results


# ----------------------------------------------------
# Global Retrieval State and Retrieval Engine
# ----------------------------------------------------

class RetrievalState:
    def __init__(self, query: str, query_embedding: Optional[List[float]], policy, search_policy: SearchPolicy):
        self.query = query
        self.query_embedding = query_embedding
        self.policy = policy
        self.search_policy = search_policy
        self.visited_entities = set()
        self.visited_chunks = set()
        self.visited_entities_order = []
        self.visited_chunks_order = []
        self.global_accepted_chunks = []
        self.discovered_paths = []
        self.scores = {}

        # Diagnostics & Scores
        self.explored_states_count = 0
        self.rejected_chunks_count = 0
        self.frontier_expansions_count = 0
        self.spawned_states_count = 0
        self.evidence_scores = []
        self.convergence_reason = "NONE"


class RetrievalEngine:
    def __init__(self, graph_repo, entity_repo, mention_repo, chunk_repo, embedding_engine=None, vector_index=None):
        self.graph_repo = graph_repo
        self.entity_repo = entity_repo
        self.mention_repo = mention_repo
        self.chunk_repo = chunk_repo
        self.embedding_engine = embedding_engine
        self.vector_index = vector_index

    def search(self, query: str, seed_entities: List[str], policy) -> RetrievalState:
        query_embedding = None
        if self.embedding_engine:
            if hasattr(self.embedding_engine, "get_query_embedding"):
                query_embedding = self.embedding_engine.get_query_embedding(query)
            elif hasattr(self.embedding_engine, "provider") and self.embedding_engine.provider:
                query_embedding = self.embedding_engine.provider.embed_text(query)

        if not policy.enable_scoring or policy.search_policy_type == "fifo":
            search_policy = FIFOSearchPolicy()
        else:
            search_policy = BestFirstSearchPolicy(alpha=policy.momentum_alpha, beta=policy.expansion_beta)

        retrieval_state = RetrievalState(query, query_embedding, policy, search_policy)

        # Initialize seeds
        for seed_id in seed_entities:
            stype = self.graph_repo.get_node_type(seed_id)
            if stype == NodeType.ENTITY:
                retrieval_state.visited_entities.add(seed_id)
                retrieval_state.visited_entities_order.append(seed_id)
            elif stype == NodeType.CHUNK:
                retrieval_state.visited_chunks.add(seed_id)
                retrieval_state.visited_chunks_order.append(seed_id)

            initial_state = SearchState(
                current_entity=seed_id,
                arrival_chunk=None,
                evidence_context=[],
                traversal_path=[seed_id],
                priority=1.0,
                depth=0
            )
            retrieval_state.search_policy.push(initial_state)
            retrieval_state.spawned_states_count += 1
            retrieval_state.scores[seed_id] = 1.0
            retrieval_state.discovered_paths.append(TraversalPath(
                seed_entity=seed_id,
                target_entity=seed_id,
                hops=[seed_id],
                relations=[],
                depth=0,
                traversal_score=1.0
            ))

        qa_scorer = QueryAlignmentScorer(self.embedding_engine, self.vector_index)
        cc_scorer = ContextContinuityScorer(self.embedding_engine, self.vector_index)
        novelty_provider = LexicalNoveltyProvider()
        ep_scorer = ExpansionPotentialScorer(self.mention_repo, retrieval_state.visited_entities)
        mrv_combiner = MRVCombiner(
            qw=policy.query_alignment_weight,
            cw=policy.context_continuity_weight,
            nw=policy.novelty_weight,
            ew=policy.expansion_potential_weight
        )
        evaluator = EvidenceEvaluator(
            qa_scorer=qa_scorer,
            cc_scorer=cc_scorer,
            novelty_provider=novelty_provider,
            ep_scorer=ep_scorer,
            mrv_combiner=mrv_combiner,
            acceptance_margin=policy.acceptance_margin
        )
        candidate_generator = CandidateGenerator(
            graph_repo=self.graph_repo,
            mention_repo=self.mention_repo,
            chunk_repo=self.chunk_repo
        )

        start_time = time.time()
        timeout_seconds = 5.0
        consecutive_misses = 0

        while not retrieval_state.search_policy.is_empty():
            if time.time() - start_time > timeout_seconds:
                retrieval_state.convergence_reason = "TIMEOUT"
                break

            if len(retrieval_state.visited_entities) >= policy.entity_budget:
                retrieval_state.convergence_reason = "ENTITY_BUDGET"
                break
            if len(retrieval_state.visited_chunks) >= policy.chunk_budget:
                retrieval_state.convergence_reason = "CHUNK_BUDGET"
                break

            state = retrieval_state.search_policy.pop()
            retrieval_state.explored_states_count += 1

            if state.depth >= policy.max_depth:
                continue

            if policy.search_policy_type == "best_first" and policy.enable_scoring:
                if state.priority < policy.min_priority_threshold:
                    retrieval_state.convergence_reason = "MIN_PRIORITY"
                    break

            expansion_candidates = candidate_generator.generate_candidates(state)
            if not expansion_candidates:
                continue
            retrieval_state.frontier_expansions_count += 1

            any_accepted_in_expansion = False

            # Collect all candidate chunks globally for this expansion step to compute a global Expansion Context Baseline (ECB)
            all_candidate_chunks = []
            chunk_to_neighbors = {}
            seen_chunks = set()
            for neighbor_id, chunks in expansion_candidates:
                if neighbor_id in state.traversal_path:
                    continue

                if policy.max_degree_threshold is not None:
                    degree = len(self.graph_repo.get_neighbors(neighbor_id))
                    if degree > policy.max_degree_threshold:
                        continue

                for chunk in chunks:
                    if chunk.id not in chunk_to_neighbors:
                        chunk_to_neighbors[chunk.id] = []
                    chunk_to_neighbors[chunk.id].append(neighbor_id)
                    if chunk.id not in seen_chunks:
                        seen_chunks.add(chunk.id)
                        all_candidate_chunks.append(chunk)

            if not all_candidate_chunks:
                continue

            eval_results = evaluator.evaluate_candidates(
                query=query,
                query_embedding=query_embedding,
                search_state=state,
                candidate_chunks=all_candidate_chunks,
                enable_scoring=policy.enable_scoring
            )

            for chunk, mrv, marginal_gain, accepted in eval_results:
                if not any(es.chunk_id == chunk.id for es in retrieval_state.evidence_scores):
                    retrieval_state.evidence_scores.append(EvidenceScore(
                        chunk_id=chunk.id,
                        mrv=mrv,
                        marginal_gain=marginal_gain
                    ))

                if accepted:
                    any_accepted_in_expansion = True
                    neighbors = chunk_to_neighbors.get(chunk.id, [])
                    for neighbor_id in neighbors:
                        retrieval_state.visited_entities.add(neighbor_id)
                        if neighbor_id not in retrieval_state.visited_entities_order:
                            retrieval_state.visited_entities_order.append(neighbor_id)
                        
                        retrieval_state.visited_chunks.add(chunk.id)
                        if chunk.id not in retrieval_state.visited_chunks_order:
                            retrieval_state.visited_chunks_order.append(chunk.id)
                        
                        if chunk not in retrieval_state.global_accepted_chunks:
                            retrieval_state.global_accepted_chunks.append(chunk)

                        if isinstance(retrieval_state.search_policy, FIFOSearchPolicy):
                            child_priority = 1.0
                        else:
                            ep_score = ep_scorer.score(chunk)
                            child_priority = retrieval_state.search_policy.calculate_priority(
                                parent_priority=state.priority,
                                immediate_mrv=mrv,
                                ep=ep_score
                            )

                        child_state = SearchState(
                            current_entity=neighbor_id,
                            arrival_chunk=chunk.id,
                            evidence_context=state.evidence_context + [chunk],
                            traversal_path=state.traversal_path + [neighbor_id],
                            priority=child_priority,
                            depth=state.depth + 1
                        )
                        retrieval_state.search_policy.push(child_state)
                        retrieval_state.spawned_states_count += 1
                        retrieval_state.scores[neighbor_id] = max(retrieval_state.scores.get(neighbor_id, 0.0), child_priority)

                        relations_between = [
                            rel.relation_type 
                            for rel in self.graph_repo.get_neighbors(state.current_entity) 
                            if (rel.source == state.current_entity and rel.target == neighbor_id) or 
                               (rel.target == state.current_entity and rel.source == neighbor_id)
                        ]
                        rel_type = relations_between[0] if relations_between else "links_to"

                        parent_path = next((p for p in retrieval_state.discovered_paths if p.target_entity == state.current_entity), None)
                        path_relations = (parent_path.relations + [rel_type]) if parent_path else [rel_type]

                        t_path = TraversalPath(
                            seed_entity=state.traversal_path[0],
                            target_entity=neighbor_id,
                            hops=state.traversal_path + [neighbor_id],
                            relations=path_relations,
                            depth=state.depth + 1,
                            traversal_score=child_priority
                        )
                        retrieval_state.discovered_paths = [
                            p for p in retrieval_state.discovered_paths 
                            if not (p.target_entity == neighbor_id and p.seed_entity == state.traversal_path[0])
                        ]
                        retrieval_state.discovered_paths.append(t_path)
                else:
                    retrieval_state.rejected_chunks_count += 1

            if any_accepted_in_expansion:
                consecutive_misses = 0
            else:
                consecutive_misses += 1

            if policy.enable_scoring and consecutive_misses >= policy.consecutive_misses_limit:
                retrieval_state.convergence_reason = "CONSECUTIVE_MISSES"
                break
        else:
            if retrieval_state.convergence_reason == "NONE":
                retrieval_state.convergence_reason = "FRONTIER_EMPTY"

        return retrieval_state
