import datetime
from typing import List
from contracts.models import KnowledgeDocument
from storage.sqlite_storage import SQLiteStorage
from ingestion.builders import ArtifactBuilder, RelationBuilder, ChunkBuilder, IndexBuilder
from ingestion.mention_extractor import MentionExtractor
from ingestion.anchor_extractor import AnchorExtractor
from utils.entity_type import EntityType


class IngestionPipeline:

    def __init__(
        self,
        storage: SQLiteStorage,
        mention_extractor: MentionExtractor,
        artifact_builder: ArtifactBuilder = None,
        relation_builder: RelationBuilder = None,
        chunk_builder: ChunkBuilder = None,
        index_builder: IndexBuilder = None,
        anchor_extractor: AnchorExtractor = None
    ):
        self.storage = storage
        self.mention_extractor = mention_extractor
        self.artifact_builder = artifact_builder or ArtifactBuilder(storage)
        self.relation_builder = relation_builder or RelationBuilder(storage)
        self.chunk_builder = chunk_builder or ChunkBuilder(storage)
        self.index_builder = index_builder or IndexBuilder(storage)
        self.anchor_extractor = anchor_extractor or AnchorExtractor(storage, mention_extractor)

    def ingest_documents(self, documents: List[KnowledgeDocument], progress_callback = None) -> dict:
        """
        Ingests a list of KnowledgeDocuments into the knowledge base database.
        Returns a dictionary of pipeline execution metrics.
        """
        start_time = datetime.datetime.now()
        if hasattr(self.storage, "bulk_transaction"):
            with self.storage.bulk_transaction():
                return self._ingest_core(documents, start_time, progress_callback)
        else:
            return self._ingest_core(documents, start_time, progress_callback)

    def _ingest_core(self, documents: List[KnowledgeDocument], start_time: datetime.datetime, progress_callback = None) -> dict:
        artifacts_created = 0
        chunks_created = 0
        relations_created = 0
        mentions_extracted = 0
        anchors_resolved = 0

        def update_progress(pct, msg):
            if progress_callback:
                progress_callback(pct, msg)
            print(f"[Ingestion {pct:.1f}%] {msg}")

        total_docs = len(documents)

        # 1. Create Artifacts and Auto-Register Anchors
        update_progress(70.0, f"Step 1/5: Ingesting {total_docs} Artifacts & Anchors...")
        for idx, doc in enumerate(documents):
            self.artifact_builder.create_artifact(doc)
            artifacts_created += 1
            
            # Auto-register canonical anchor for this page
            existing_anchor = self.anchor_extractor.anchor_resolver.resolve(doc.title, create_if_missing=False)
            if not existing_anchor:
                anchor = self.anchor_extractor.anchor_resolver.resolve(
                    doc.title,
                    create_if_missing=True,
                    default_type=EntityType.CONCEPT
                )
                anchors_resolved += 1
            else:
                anchor = existing_anchor
            
            # Generate simplified aliases (e.g. Kitsune, Vishap)
            self.anchor_extractor.anchor_resolver.generate_and_register_simplified_aliases(anchor)
            
            if idx % 100 == 0 and idx > 0:
                update_progress(70.0 + (idx / total_docs) * 5.0, f"Ingested {idx}/{total_docs} artifacts...")

        # 2. Create structural links_to relations and process redirects
        update_progress(75.0, "Step 2/5: Resolving structural document links & redirects...")
        for idx, doc in enumerate(documents):
            rels = self.relation_builder.create_relations(doc, documents)
            relations_created += len(rels)
            
            # Process redirects_to mappings to register aliases in resolver
            for ref in doc.references:
                if ref.reference_type == "redirects_to":
                    source_title = ref.source_document.split(":")[-1].replace("_", " ")
                    target_title = ref.target_document.split(":")[-1].replace("_", " ")
                    self.anchor_extractor.anchor_resolver.register_redirect(source_title, target_title)
            
            if idx % 100 == 0 and idx > 0:
                update_progress(75.0 + (idx / total_docs) * 5.0, f"Resolved links for {idx}/{total_docs} documents...")

        # 3. Create Chunks, generate embeddings, and contains relations (Artifact -> contains -> Chunk)
        update_progress(80.0, "Step 3/5: Segmenting text chunks and indexing containments...")
        all_chunks = []
        for idx, doc in enumerate(documents):
            chunks = self.chunk_builder.create_chunks(doc.id, doc.sections)
            # Generate embeddings (mock-implemented in V1 to keep decoulped)
            self.chunk_builder.generate_embeddings(chunks)
            chunks_created += len(chunks)
            relations_created += len(chunks)  # 'contains' is also a relation
            all_chunks.extend(chunks)
            if idx % 100 == 0 and idx > 0:
                update_progress(80.0 + (idx / total_docs) * 5.0, f"Segmented chunks for {idx}/{total_docs} documents...")

        # 4. Extract Entity Mentions and resolve/persist Anchors using AnchorExtractor
        total_chunks = len(all_chunks)
        update_progress(85.0, f"Step 4/5: Running Entity Mention Extractor on {total_chunks} text chunks...")
        
        # Dynamically refresh mention vocabulary from entities and aliases registered in DB
        if hasattr(self.mention_extractor, "set_known_terms"):
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT canonical_name FROM entities")
                names = [row[0] for row in cursor.fetchall()]
                cursor.execute("SELECT alias FROM aliases")
                aliases = [row[0] for row in cursor.fetchall()]
            self.mention_extractor.set_known_terms(set(names + aliases))

        new_anchors, total_mentions, new_relations = self.anchor_extractor.extract_anchors(all_chunks, progress_callback)
        anchors_resolved += new_anchors
        mentions_extracted += total_mentions
        relations_created += new_relations

        # 5. Build/refresh search index structures
        update_progress(98.0, "Step 5/5: Rebuilding SQLite indexing and search structures...")
        self.index_builder.refresh_indexes()
        update_progress(100.0, "Pipeline completed successfully.")

        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "artifacts_created": artifacts_created,
            "chunks_created": chunks_created,
            "relations_created": relations_created,
            "mentions_extracted": mentions_extracted,
            "anchors_resolved": anchors_resolved,
            "duration": round(duration, 3)
        }
