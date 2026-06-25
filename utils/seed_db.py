import json
import os
from storage.sqlite_storage import SQLiteStorage
from storage.entity_repository import EntityRepository
from storage.artifact_repository import ArtifactRepository
from storage.chunk_repository import ChunkRepository
from storage.mention_repository import MentionRepository
from storage.link_repository import LinkRepository
from utils.entity_type import EntityType


def seed_database(storage: SQLiteStorage, corpus_file_path: str):
    # Initialize repositories
    entity_repo = EntityRepository(storage)
    artifact_repo = ArtifactRepository(storage)
    chunk_repo = ChunkRepository(storage)
    mention_repo = MentionRepository(storage)
    link_repo = LinkRepository(storage)

    print("--- Seeding Database ---")

    # 1. Clean existing data in correct dependency order
    with storage.get_connection() as conn:
        cursor = conn.cursor()
        tables = [
            "artifact_links",
            "entity_mentions",
            "aliases",
            "chunks",
            "artifacts",
            "entities",
            "relations"
        ]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
    print("Cleared existing tables.")

    # Load corpus
    with open(corpus_file_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # 2. First Pass: Create Entities and Artifacts
    entity_id_map = {}   # title (lower) -> entity_id
    artifact_id_map = {} # title (lower) -> artifact_id

    for page in corpus:
        title = page["title"]
        entity_type_str = page["entity_type"]
        source_type = page["source_type"]
        source = page["source"]

        # Create Entity
        entity = entity_repo.create(
            canonical_name=title,
            entity_type=EntityType(entity_type_str),
            metadata={"source": "handcrafted_corpus"}
        )
        entity_id_map[title.lower()] = entity.id

        # Create Artifact
        artifact = artifact_repo.create(
            title=title,
            source_type=source_type,
            source=source,
            metadata={"entity_id": entity.id}
        )
        artifact_id_map[title.lower()] = artifact.id

    print(f"Created {len(entity_id_map)} Entities and Artifacts.")

    # 3. Second Pass: Create Chunks, Detect Mentions, and Add Links
    for page in corpus:
        title = page["title"]
        content = page["content"]
        outgoing_links = page["outgoing_links"]

        art_id = artifact_id_map[title.lower()]

        # Split content into sentences to make multiple chunks
        sentences = [s.strip() for s in content.split(".") if s.strip()]
        chunks_text = []
        for i in range(0, len(sentences), 2):
            chunk_txt = ". ".join(sentences[i:i+2])
            if not chunk_txt.endswith("."):
                chunk_txt += "."
            chunks_text.append(chunk_txt)

        # Create Chunks & Mentions
        for chunk_txt in chunks_text:
            chunk = chunk_repo.create(
                artifact_id=art_id,
                content=chunk_txt,
                metadata={"length": len(chunk_txt)}
            )

            # Auto-detect mentions in the chunk content
            for ent_name_lower, ent_id in entity_id_map.items():
                # Check for case-insensitive containment
                if ent_name_lower in chunk_txt.lower():
                    mention_repo.add(entity_id=ent_id, chunk_id=chunk.id)

        # Create Links
        source_art_id = artifact_id_map[title.lower()]
        for target_title in outgoing_links:
            target_lower = target_title.lower()
            if target_lower in artifact_id_map:
                target_art_id = artifact_id_map[target_lower]
                link_repo.add(source_art_id, target_art_id)
            else:
                print(f"Warning: Outgoing link '{target_title}' on page '{title}' does not exist in corpus.")

    print("Corpus seeding complete.")
