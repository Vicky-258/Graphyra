import json
import os
import datetime
from storage.sqlite_storage import SQLiteStorage
from storage.entity_repository import EntityRepository
from storage.artifact_repository import ArtifactRepository
from storage.chunk_repository import ChunkRepository
from storage.mention_repository import MentionRepository
from storage.link_repository import LinkRepository
from utils.entity_type import EntityType
from models.alias import Alias
from models.evidence_reference import EvidenceReference
from models.relation import Relation


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
            "evidence_references",
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

    # 2. First Pass: Create Entities, Aliases, and Artifacts
    entity_id_map = {}   # title (lower) -> entity_id
    artifact_id_map = {} # title (lower) -> artifact_id

    # Predefined aliases for the demo corpus
    aliases_map = {
        "Nahida": ["Lesser Lord Kusanali", "Buer", "Kusanali"],
        "Greater Lord Rukkhadevata": ["Rukkhadevata"],
        "Akasha System": ["Akasha"],
        "Il Dottore": ["The Doctor"]
    }

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

        # Seed aliases if predefined
        if title in aliases_map:
            for alias_name in aliases_map[title]:
                storage.add_alias(Alias(entity_id=entity.id, alias=alias_name))

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

        # Create Chunks, Contains Relations & Mentions
        for chunk_txt in chunks_text:
            chunk = chunk_repo.create(
                artifact_id=art_id,
                content=chunk_txt,
                metadata={"length": len(chunk_txt)}
            )

            # Add 'contains' relation
            storage.create_relation(Relation(
                id="",
                source_id=art_id,
                target_id=chunk.id,
                relation_type="contains"
            ))

            # Auto-detect mentions in the chunk content (canonical and aliases)
            for ent_name_lower, ent_id in entity_id_map.items():
                ent_obj = entity_repo.get(ent_id)
                names_to_check = [ent_name_lower]
                if ent_obj:
                    names_to_check.extend([a.lower() for a in storage.get_aliases(ent_id)])

                # If any of the names/aliases are found in this chunk text
                is_mentioned = False
                for name_to_check in names_to_check:
                    # check word boundaries or simple substring for multi-word aliases
                    if name_to_check in chunk_txt.lower():
                        is_mentioned = True
                        break

                if is_mentioned:
                    mention_repo.add(entity_id=ent_id, chunk_id=chunk.id)
                    
                    # Store evidence reference for entity mention
                    storage.add_evidence(EvidenceReference(
                        id="",
                        artifact_id=art_id,
                        chunk_id=chunk.id,
                        extraction_method="heuristics_mention_detection",
                        confidence=1.0,
                        timestamp=datetime.datetime.now().isoformat(),
                        entity_id=ent_id
                    ))
                    
                    # Store matching mentions relation in the relations table
                    rel_obj = storage.create_relation(Relation(
                        id="",
                        source_id=chunk.id,
                        target_id=ent_id,
                        relation_type="mentions"
                    ))
                    
                    # Store evidence reference for mentions relation
                    storage.add_evidence(EvidenceReference(
                        id="",
                        artifact_id=art_id,
                        chunk_id=chunk.id,
                        extraction_method="heuristics_mention_relation",
                        confidence=1.0,
                        timestamp=datetime.datetime.now().isoformat(),
                        relation_id=rel_obj.id
                    ))

        # Create Links & Links Relations
        source_art_id = artifact_id_map[title.lower()]
        for target_title in outgoing_links:
            target_lower = target_title.lower()
            if target_lower in artifact_id_map:
                target_art_id = artifact_id_map[target_lower]
                link_repo.add(source_art_id, target_art_id)

                # Add link relation to relations table
                rel_obj = storage.create_relation(Relation(
                    id="",
                    source_id=source_art_id,
                    target_id=target_art_id,
                    relation_type="links_to"
                ))

                # Determine evidence chunk in the source artifact that motivated this link
                source_chunks = chunk_repo.get_by_artifact(source_art_id)
                evidence_chunk_id = source_chunks[0].id if source_chunks else ""
                for chk in source_chunks:
                    if target_title.lower() in chk.content.lower():
                        evidence_chunk_id = chk.id
                        break

                # Add evidence reference for the links_to relation
                storage.add_evidence(EvidenceReference(
                    id="",
                    artifact_id=source_art_id,
                    chunk_id=evidence_chunk_id,
                    extraction_method="parser_hyperlink",
                    confidence=1.0,
                    timestamp=datetime.datetime.now().isoformat(),
                    relation_id=rel_obj.id
                ))
            else:
                print(f"Warning: Outgoing link '{target_title}' on page '{title}' does not exist in corpus.")

    print("Corpus seeding complete.")
