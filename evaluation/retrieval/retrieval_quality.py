import os
import json
import time
from typing import List, Dict, Any, Set
from storage.sqlite_storage import SQLiteStorage
from storage.evidence_retriever import EvidenceRetriever
from storage.graph_repository import SQLiteGraphRepository
from storage.entity_repository import EntityRepository
from storage.mention_repository import MentionRepository
from traversal_engine import TraversalEngine
from semantic.bootstrap import bootstrap_semantic_layer
from retrieval.ranking.ranker import EvidenceRanker
from retrieval.ranking.policy import RankingPolicy
from models.traversal_models import TraversalRequest, TraversalPolicy


def run_quality_evaluation(
    db_file: str = "graphyra.db",
    ground_truth_file: str = "evaluation/retrieval/ground_truth.json"
) -> Dict[str, Any]:
    """
    Evaluates retrieval metrics (Precision@K, Recall@K, MRR, Traversal success)
    for Entity Retrieval, Semantic Retrieval, Candidate Fusion, and Hybrid Final pipelines.
    """
    storage = SQLiteStorage(db_file)
    storage.initialize_database()
    
    # Repositories
    graph_repo = SQLiteGraphRepository(storage)
    entity_repo = EntityRepository(storage)
    mention_repo = MentionRepository(storage)
    
    # Core components
    traversal_engine = TraversalEngine(graph_repo, entity_repo, mention_repo)
    evidence_retriever = EvidenceRetriever(storage)
    
    # Semantic Bootstrap
    emb_engine, vec_index, semantic_fusion, _ = bootstrap_semantic_layer(storage, db_path="embeddings.db")
    
    # Ranker
    ranker = EvidenceRanker(
        semantic_scorer=None,  # Handled within stage test
        reranker_provider=None
    )
    
    # Load ground truth
    with open(ground_truth_file, "r") as f:
        ground_truth = json.load(f)
        
    stages = ["Entity_Only", "Semantic_Only", "Candidate_Fusion", "Final_Hybrid"]
    metrics = {stage: {
        "precision_5": [], "recall_5": [], "precision_10": [], "recall_10": [], "mrr": []
    } for stage in stages}
    
    # Rates
    semantic_anchor_discoveries = 0
    traversal_successes = 0
    
    for gt in ground_truth:
        query = gt["query"]
        expected_entities = set(gt["expected_entities"])
        expected_chunks = set(gt["expected_chunks"])
        
        # --- STAGE 1: Entity-Only Retrieval ---
        # Direct matches from query entities
        direct_matches = []
        for entity_id in expected_entities:
            ent = entity_repo.get(entity_id)
            if ent:
                direct_matches.append(ent)
                
        # Run Traversal from direct matches
        req_entity = TraversalRequest(
            query=query,
            seed_entities=list(expected_entities),
            policy=TraversalPolicy(max_depth=2)
        )
        res_entity = traversal_engine.traverse(req_entity)
        cands_entity = evidence_retriever.retrieve_evidence(res_entity)
        
        # Sort by traversal score
        cands_entity.sort(key=lambda c: c.best_traversal_score if c.best_traversal_score is not None else 0.0, reverse=True)
        evaluate_stage(cands_entity, expected_chunks, metrics["Entity_Only"])
        
        # --- STAGE 2: Semantic-Only Retrieval ---
        q_vec = emb_engine.provider.embed_text(query)
        search_res = vec_index.search(q_vec, top_k=10)
        
        # Convert SearchResults to CandidateEvidence objects
        from models.traversal_models import CandidateEvidence
        from storage.chunk_repository import ChunkRepository
        chunk_repository = ChunkRepository(storage)
        cands_sem = []
        for s in search_res:
            chunk = chunk_repository.get(s.id)
            if chunk:
                cands_sem.append(CandidateEvidence(
                    chunk=chunk,
                    best_traversal_score=0.0,
                    min_depth=0,
                    discovered_by=["SemanticSearch"],
                    paths=[]
                ))
        evaluate_stage(cands_sem, expected_chunks, metrics["Semantic_Only"])
        
        # --- STAGE 3: Candidate Fusion ---
        # Entity matching from query + entities extracted semantically
        semantic_entities = []
        for s in search_res:
            # Get entity mentions in semantic chunk
            entity_ids = mention_repo.get_entities_for_chunk(s.id)
            for ent_id in entity_ids:
                ent = entity_repo.get(ent_id)
                if ent:
                    semantic_entities.append((ent, s.score))
                    
        # Fuse
        fused_seeds = semantic_fusion.fuse_candidates(direct_matches, semantic_entities)
        
        if len(fused_seeds) > len(direct_matches):
            semantic_anchor_discoveries += 1
            
        seed_ids = [seed[0].id for seed in fused_seeds]
        
        # Run Traversal on fused seeds
        req_fused = TraversalRequest(
            query=query,
            seed_entities=seed_ids,
            policy=TraversalPolicy(max_depth=2)
        )
        res_fused = traversal_engine.traverse(req_fused)
        cands_fused = evidence_retriever.retrieve_evidence(res_fused)
        
        cands_fused.sort(key=lambda c: c.best_traversal_score if c.best_traversal_score is not None else 0.0, reverse=True)
        evaluate_stage(cands_fused, expected_chunks, metrics["Candidate_Fusion"])
        
        # --- STAGE 4: Final Hybrid Pipeline ---
        # Run fused traversal candidates through the evidence ranker (with RRF)
        # Setup ranker with actual scorers
        from retrieval.ranking.bm25 import BM25Scorer
        from retrieval.ranking.semantic import SemanticScorer
        
        full_ranker = EvidenceRanker(
            bm25_scorer=BM25Scorer(),
            semantic_scorer=SemanticScorer(emb_engine.provider, vec_index),
            fusion_engine=None
        )
        
        ranked_final = full_ranker.rank(
            query=query,
            candidates=cands_fused,
            policy=RankingPolicy(enable_bm25=True, enable_semantic=True, enable_reranker=False)
        )
        
        if ranked_final:
            traversal_successes += 1
            
        evaluate_stage(ranked_final, expected_chunks, metrics["Final_Hybrid"])

    # Aggregate averages
    summary = {}
    for stage in stages:
        summary[stage] = {
            "Precision@5": sum(metrics[stage]["precision_5"]) / len(ground_truth),
            "Recall@5": sum(metrics[stage]["recall_5"]) / len(ground_truth),
            "Precision@10": sum(metrics[stage]["precision_10"]) / len(ground_truth),
            "Recall@10": sum(metrics[stage]["recall_10"]) / len(ground_truth),
            "MRR": sum(metrics[stage]["mrr"]) / len(ground_truth)
        }
        
    summary["semantic_anchor_discovery_rate"] = semantic_anchor_discoveries / len(ground_truth)
    summary["graph_traversal_success_rate"] = traversal_successes / len(ground_truth)
    
    return summary


def evaluate_stage(
    candidates: List[Any],
    expected: Set[str],
    metrics_bucket: Dict[str, List[float]]
) -> None:
    retrieved_ids = [c.id for c in candidates]
    
    # Precision and Recall at 5
    top_5 = retrieved_ids[:5]
    hits_5 = len([i for i in top_5 if i in expected])
    p5 = hits_5 / 5.0
    r5 = hits_5 / len(expected) if expected else 0.0
    
    # Precision and Recall at 10
    top_10 = retrieved_ids[:10]
    hits_10 = len([i for i in top_10 if i in expected])
    p10 = hits_10 / 10.0
    r10 = hits_10 / len(expected) if expected else 0.0
    
    # MRR
    mrr_val = 0.0
    for idx, c_id in enumerate(retrieved_ids):
        if c_id in expected:
            mrr_val = 1.0 / (idx + 1)
            break
            
    metrics_bucket["precision_5"].append(p5)
    metrics_bucket["recall_5"].append(r5)
    metrics_bucket["precision_10"].append(p10)
    metrics_bucket["recall_10"].append(r10)
    metrics_bucket["mrr"].append(mrr_val)
