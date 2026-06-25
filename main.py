import os
from storage.sqlite_storage import SQLiteStorage
from utils.seed_db import seed_database
from engine import Graphyra


def main():
    db_file = "graphyra.db"
    storage = SQLiteStorage(db_file)
    storage.initialize_database()

    # Seed the database
    corpus_file = os.path.join("data", "sumeru_demo_corpus.json")
    seed_database(storage, corpus_file)

    # Initialize Graphyra Traversal Engine
    graphyra = Graphyra(storage)

    # Trigger Reasoning Trace
    question = "Who taught Nahida about Irminsul?"
    print(f"--- Running Reasoning Trace for: \"{question}\" ---\n")
    graphyra.explain(question)
    print()


if __name__ == "__main__":
    main()