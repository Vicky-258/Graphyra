import os
import time
import json
import numpy as np
from typing import List, Dict, Any
from storage.sqlite_storage import SQLiteStorage
from storage.chunk_repository import ChunkRepository
from semantic.providers.sentence_transformer import SentenceTransformerProvider
from semantic.engine import EmbeddingEngine


def benchmark_models(
    models: List[str],
    chunks_limit: int,
    db_file: str = "graphyra.db"
) -> Dict[str, Any]:
    """
    Evaluates inference, throughput, load time, and latencies across multiple embedding models.
    """
    storage = SQLiteStorage(db_file)
    chunk_repo = ChunkRepository(storage)
    all_chunks = chunk_repo.list_all()
    
    # Restrict to chunks_limit for speed
    test_chunks = all_chunks[:chunks_limit]
    texts = [c.content for c in test_chunks]
    
    results = {}
    
    for model_name in models:
        print(f"\n--- Benchmarking Model: {model_name} (subset: {len(test_chunks)} chunks) ---")
        
        # 1. Measure load time
        start_t = time.time()
        provider = None
        load_error = None
        try:
            provider = SentenceTransformerProvider(model_name=model_name)
            load_time = time.time() - start_t
            print(f"Loaded in {load_time:.2f}s.")
        except Exception as e:
            load_error = str(e)
            load_time = 0.0
            print(f"Failed to load: {e}")
            
        if provider is None:
            results[model_name] = {
                "compatible": False,
                "error": load_error
            }
            continue
            
        engine = EmbeddingEngine(provider)
        
        # 2. Get dimensions
        dimension = provider.dimension
        
        # 3. CPU Inference speed / throughput
        batch_size = 64
        inference_latencies = []
        
        start_t = time.time()
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            b_start = time.time()
            _ = engine.get_chunks_embeddings(batch)
            inference_latencies.append(time.time() - b_start)
        
        rebuild_time = time.time() - start_t
        throughput = len(texts) / rebuild_time if rebuild_time > 0 else 0.0
        
        # 4. Average query embedding latency
        query_latencies = []
        queries = ["Who is Nahida?", "Akasha System", "Raiden Ei Inazuma", "Irminsul tree connection"]
        for q in queries:
            q_start = time.time()
            _ = provider.embed_text(q)
            query_latencies.append(time.time() - q_start)
            
        avg_query_ms = (sum(query_latencies) / len(query_latencies)) * 1000
        avg_batch_ms = (sum(inference_latencies) / len(inference_latencies)) * 1000 if inference_latencies else 0.0
        
        results[model_name] = {
            "compatible": True,
            "dimension": dimension,
            "load_time_s": load_time,
            "rebuild_time_s": rebuild_time,
            "throughput_cps": throughput,
            "avg_query_ms": avg_query_ms,
            "avg_batch_ms": avg_batch_ms,
            "num_chunks_tested": len(test_chunks)
        }
        
    return results
