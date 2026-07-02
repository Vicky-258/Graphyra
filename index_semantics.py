import os
import sys
from storage.sqlite_storage import SQLiteStorage
from semantic.bootstrap import bootstrap_semantic_layer


def run_indexing():
    db_file = "graphyra.db"
    if not os.path.exists(db_file):
        print(f"Error: Knowledge Graph base database '{db_file}' not found.")
        sys.exit(1)
        
    print(f"Initializing Graphyra storage on {db_file}...")
    storage = SQLiteStorage(db_file)
    
    print("Bootstrapping semantic indexing layer...")
    # Bootstrap using virtual env configuration
    emb_engine, vec_index, fus_engine, indexer = bootstrap_semantic_layer(storage, db_path="embeddings.db")
    
    model_name = getattr(emb_engine.provider, "model_name", "mock_model")
    print(f"Active embedding provider: {emb_engine.provider.__class__.__name__}")
    print(f"Target model: {model_name}")
    
    # 1. Check and automatically rebuild if model configuration has drifted
    print("Checking model compatibility / drift status...")
    rebuilt = indexer.verify_and_rebuild_if_needed()
    if rebuilt:
        print("Semantic index model drift detected. Rebuild completed successfully.")
        return

    # 2. Check and index any missing chunks incrementally
    print("Scanning database for unindexed chunks...")
    indexed_count = indexer.index_missing_chunks()
    if indexed_count > 0:
        print(f"Successfully generated embeddings and indexed {indexed_count} new chunks.")
    else:
        print("All chunks are already up-to-date in the semantic index.")


if __name__ == "__main__":
    run_indexing()
