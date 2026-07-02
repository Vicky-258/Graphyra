import os
import time
import tempfile
from typing import List, Dict, Any
from semantic.index import SQLiteVectorIndex, FaissVectorIndex, HnswlibVectorIndex


def benchmark_backends(
    num_elements: int = 1000,
    dimension: int = 384
) -> Dict[str, Any]:
    """
    Benchmarks SQLite, FAISS, and HNSWlib backends.
    Catches ImportErrors cleanly if platform dependencies are missing.
    """
    import numpy as np
    
    # Generate test vectors and keys
    np.random.seed(42)
    vectors = np.random.rand(num_elements, dimension).astype(np.float32).tolist()
    ids = [f"CHK_{i:04d}" for i in range(num_elements)]
    
    # Define backends to test
    backends = {
        "SQLiteVectorIndex": SQLiteVectorIndex,
        "FaissVectorIndex": FaissVectorIndex,
        "HnswlibVectorIndex": HnswlibVectorIndex
    }
    
    results = {}
    
    for name, index_cls in backends.items():
        print(f"\n--- Benchmarking Backend: {name} ---")
        
        # 1. Startup / Loading Time
        start_t = time.time()
        temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(temp_dir.name, f"test_{name.lower()}.db")
        
        try:
            # Instantiate indexer
            index = index_cls(db_path=db_path, model_name="all-MiniLM-L6-v2")
            startup_time = time.time() - start_t
        except ImportError as ie:
            print(f"Skipping {name}: dependency not installed ({ie})")
            results[name] = {"compatible": False, "error": str(ie)}
            temp_dir.cleanup()
            continue
        except Exception as e:
            print(f"Skipping {name}: failed to initialize ({e})")
            results[name] = {"compatible": False, "error": str(e)}
            temp_dir.cleanup()
            continue
            
        # 2. Insert throughput / build time
        start_t = time.time()
        for i, v in zip(ids, vectors):
            index.add_vector(i, v)
        build_time = time.time() - start_t
        insert_throughput = num_elements / build_time if build_time > 0 else 0.0
        
        # 3. Query latency / Search throughput
        query_vector = np.random.rand(dimension).astype(np.float32).tolist()
        
        # Measure search latency (100 runs)
        search_times = []
        for _ in range(100):
            s_start = time.time()
            _ = index.search(query_vector, top_k=5)
            search_times.append(time.time() - s_start)
            
        avg_query_ms = (sum(search_times) / len(search_times)) * 1000
        search_throughput = 100 / sum(search_times) if sum(search_times) > 0 else 0.0
        
        # 4. Storage size
        storage_size_bytes = 0
        if os.path.exists(db_path):
            storage_size_bytes = os.path.getsize(db_path)
            
        # 5. Incremental update performance
        # Insert 10 replacement/new vectors
        start_t = time.time()
        for idx in range(10):
            index.add_vector(f"NEW_{idx}", query_vector)
        incremental_time_ms = (time.time() - start_t) * 1000
        
        results[name] = {
            "compatible": True,
            "startup_s": startup_time,
            "build_s": build_time,
            "insert_throughput_vps": insert_throughput,
            "avg_query_ms": avg_query_ms,
            "search_throughput_qps": search_throughput,
            "storage_size_kb": storage_size_bytes / 1024.0,
            "incremental_update_ms": incremental_time_ms
        }
        
        # Cleanup
        index.clear()
        temp_dir.cleanup()
        
    return results
