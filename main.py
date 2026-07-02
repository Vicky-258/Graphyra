import os
from storage.sqlite_storage import SQLiteStorage
from utils.seed_db import seed_database
from engine import Graphyra


def main():
    db_file = "graphyra.db"
    storage = SQLiteStorage(db_file)
    storage.initialize_database()

    # Seed the database
    corpus_file = os.path.join("data", "genshin_500_docs.json")
    seed_database(storage, corpus_file)

    # Initialize Graphyra Traversal Engine
    from semantic.bootstrap import bootstrap_semantic_layer
    emb_engine, vec_index, fus_engine, indexer = bootstrap_semantic_layer(storage, db_path="embeddings.db")
    graphyra = Graphyra(
        storage=storage,
        embedding_engine=emb_engine,
        vector_index=vec_index,
        fusion_engine=fus_engine
    )

    # Trigger Reasoning Trace
    question = "Who taught Nahida about Irminsul?"
    print(f"--- Running Reasoning Trace for: \"{question}\" ---\n")
    graphyra.explain(question)
    print()


if __name__ == "__main__":
    main()