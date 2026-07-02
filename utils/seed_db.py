import json
import os
import datetime
from storage.sqlite_storage import SQLiteStorage
from contracts.models import KnowledgeDocument, Section, ContentBlock, Reference
from ingestion.pipeline import IngestionPipeline
from ingestion.mention_extractor import DictionaryMentionExtractor
from semantic.bootstrap import bootstrap_semantic_layer


def deserialize_doc(d: dict) -> KnowledgeDocument:
    sections = []
    for s in d.get("sections", []):
        content_blocks = []
        for b in s.get("content_blocks", []):
            content_blocks.append(ContentBlock(type=b["type"], content=b["content"]))
        sections.append(Section(id=s["id"], title=s["title"], content_blocks=content_blocks))
        
    references = []
    for r in d.get("references", []):
        references.append(Reference(
            source_document=r["source_document"],
            source_anchor=r["source_anchor"],
            target_document=r["target_document"],
            target_anchor=r["target_anchor"],
            reference_type=r["reference_type"]
        ))
        
    return KnowledgeDocument(
        id=d["id"],
        title=d["title"],
        source_type=d["source_type"],
        metadata=d.get("metadata", {}),
        sections=sections,
        references=references
    )


def seed_database(storage: SQLiteStorage, corpus_file_path: str):
    print("--- Seeding Database ---")

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

    print(f"Loading corpus from {corpus_file_path}...")
    with open(corpus_file_path, "r", encoding="utf-8") as f:
        raw_docs = json.load(f)
    documents = [deserialize_doc(d) for d in raw_docs]
    print(f"Loaded {len(documents)} documents.")

    vocabulary = set()
    for doc in documents:
        vocabulary.add(doc.title)
        for ref in doc.references:
            if ref.reference_type == "redirects_to":
                source_title = ref.source_document.split(":")[-1].replace("_", " ")
                vocabulary.add(source_title)
                
    extractor = DictionaryMentionExtractor(vocabulary)
    pipeline = IngestionPipeline(storage, extractor)

    print(f"Running IngestionPipeline on {len(documents)} documents...")
    metrics = pipeline.ingest_documents(documents)
    print(f"Successfully seeded database: {metrics}")

    print("Refreshing semantic embeddings index...")
    emb_engine, vec_index, _, indexer = bootstrap_semantic_layer(storage, db_path="embeddings.db")
    vec_index.clear()
    vec_index.load_index()
    indexed_count = indexer.index_missing_chunks()
    print(f"Semantic index refreshed: {indexed_count} chunks indexed.")
