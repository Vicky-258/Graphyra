import sqlite3
import shutil
import os


def duplicate_relational_data(db_path: str, prefixes: list):
    """
    Duplicates all database records in the SQLite file, prefixing IDs
    to simulate a scaled relational graph.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Read original data
    cursor.execute("SELECT * FROM artifacts")
    orig_artifacts = cursor.fetchall()
    
    cursor.execute("SELECT * FROM chunks")
    orig_chunks = cursor.fetchall()
    
    cursor.execute("SELECT * FROM entities")
    orig_entities = cursor.fetchall()
    
    cursor.execute("SELECT * FROM aliases")
    orig_aliases = cursor.fetchall()
    
    cursor.execute("SELECT * FROM entity_mentions")
    orig_mentions = cursor.fetchall()
    
    cursor.execute("SELECT * FROM relations")
    orig_relations = cursor.fetchall()
    
    cursor.execute("SELECT * FROM artifact_links")
    orig_links = cursor.fetchall()
    
    cursor.execute("SELECT * FROM evidence_references")
    orig_evidence = cursor.fetchall()
    
    # Duplicate records
    for prefix in prefixes:
        # 1. Artifacts (id, title, source_type, source, metadata)
        dup_artifacts = [
            (f"{prefix}{r[0]}", r[1], r[2], r[3], r[4]) for r in orig_artifacts
        ]
        cursor.executemany("INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?, ?, ?)", dup_artifacts)
        
        # 2. Chunks (id, artifact_id, content, embedding, metadata)
        dup_chunks = [
            (f"{prefix}{r[0]}", f"{prefix}{r[1]}", r[2], r[3], r[4]) for r in orig_chunks
        ]
        cursor.executemany("INSERT OR IGNORE INTO chunks VALUES (?, ?, ?, ?, ?)", dup_chunks)
        
        # 3. Entities (id, canonical_name, entity_type, metadata)
        dup_entities = [
            (f"{prefix}{r[0]}", r[1], r[2], r[3]) for r in orig_entities
        ]
        cursor.executemany("INSERT OR IGNORE INTO entities VALUES (?, ?, ?, ?)", dup_entities)
        
        # 4. Aliases (entity_id, alias)
        dup_aliases = [
            (f"{prefix}{r[0]}", r[1]) for r in orig_aliases
        ]
        cursor.executemany("INSERT OR IGNORE INTO aliases VALUES (?, ?)", dup_aliases)
        
        # 5. Mentions (entity_id, chunk_id)
        dup_mentions = [
            (f"{prefix}{r[0]}", f"{prefix}{r[1]}") for r in orig_mentions
        ]
        cursor.executemany("INSERT OR IGNORE INTO entity_mentions VALUES (?, ?)", dup_mentions)
        
        # 6. Relations (id, source_id, target_id, relation_type, metadata)
        dup_relations = [
            (f"{prefix}{r[0]}", f"{prefix}{r[1]}", f"{prefix}{r[2]}", r[3], r[4]) for r in orig_relations
        ]
        cursor.executemany("INSERT OR IGNORE INTO relations VALUES (?, ?, ?, ?, ?)", dup_relations)
        
        # 7. Artifact Links (source_artifact_id, target_artifact_id)
        dup_links = [
            (f"{prefix}{r[0]}", f"{prefix}{r[1]}") for r in orig_links
        ]
        cursor.executemany("INSERT OR IGNORE INTO artifact_links VALUES (?, ?)", dup_links)
        
        # 8. Evidence References (id, artifact_id, chunk_id, extraction_method, confidence, timestamp, entity_id, relation_id)
        dup_evidence = [
            (
                f"{prefix}{r[0]}",
                f"{prefix}{r[1]}",
                f"{prefix}{r[2]}",
                r[3],
                r[4],
                r[5],
                f"{prefix}{r[6]}" if r[6] else None,
                f"{prefix}{r[7]}" if r[7] else None
            ) for r in orig_evidence
        ]
        cursor.executemany("INSERT OR IGNORE INTO evidence_references VALUES (?, ?, ?, ?, ?, ?, ?, ?)", dup_evidence)
        
    conn.commit()
    conn.close()
    print(f"Relational database duplication complete for: {db_path}")


def duplicate_embeddings_data(db_path: str, prefixes: list):
    """
    Duplicates vectors in the SQLite embedding database, prefixing IDs
    to match the scaled relational graph.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vectors")
    orig_vectors = cursor.fetchall()
    
    for prefix in prefixes:
        dup_vectors = [
            (f"{prefix}{r[0]}", r[1]) for r in orig_vectors
        ]
        cursor.executemany("INSERT OR IGNORE INTO vectors VALUES (?, ?)", dup_vectors)
        
    conn.commit()
    conn.close()
    print(f"Embeddings database duplication complete for: {db_path}")


def generate_scaled_datasets():
    # 1. 500 Pages
    shutil.copyfile("graphyra.db", "graphyra_500.db")
    shutil.copyfile("embeddings.db", "embeddings_500.db")
    
    # 2. 1000 Pages (x2 original data size)
    shutil.copyfile("graphyra.db", "graphyra_1000.db")
    shutil.copyfile("embeddings.db", "embeddings_1000.db")
    duplicate_relational_data("graphyra_1000.db", ["s1_"])
    duplicate_embeddings_data("embeddings_1000.db", ["s1_"])
    
    # 3. 2000 Pages (x4 original data size)
    shutil.copyfile("graphyra.db", "graphyra_2000.db")
    shutil.copyfile("embeddings.db", "embeddings_2000.db")
    duplicate_relational_data("graphyra_2000.db", ["s1_", "s2_", "s3_"])
    duplicate_embeddings_data("embeddings_2000.db", ["s1_", "s2_", "s3_"])


if __name__ == "__main__":
    generate_scaled_datasets()
