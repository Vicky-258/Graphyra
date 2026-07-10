import json
from typing import List
from graphyra.models.artifact import Artifact
from graphyra.models.chunk import Chunk
from graphyra.models.relation import Relation
from graphyra.interfaces.models import KnowledgeDocument, Section
from graphyra.storage.artifact_repository import ArtifactRepository
from graphyra.storage.relation_repository import RelationRepository
from graphyra.storage.chunk_repository import ChunkRepository


class ArtifactBuilder:

    def __init__(self, storage):
        self.storage = storage
        self.artifact_repo = ArtifactRepository(storage)
        self.relation_repo = RelationRepository(storage)
        self.chunk_repo = ChunkRepository(storage)

    def create_artifact(self, doc: KnowledgeDocument) -> Artifact:
        """
        Creates an Artifact record from a KnowledgeDocument, preserving stable doc.id identity.
        If an artifact with the same ID already exists, it is overwritten.
        """
        # Overwrite existing artifact if it exists to maintain stable invariant
        self.artifact_repo.delete(doc.id)

        # Clear associated chunks, relations, and mentions for this artifact to prevent leaks using repositories
        self.relation_repo.delete_by_node(doc.id)
        self.chunk_repo.delete_by_artifact(doc.id)

        # Create new artifact
        artifact = self.artifact_repo.create(
            title=doc.title,
            source_type=doc.source_type,
            source=doc.id,
            metadata=doc.metadata,
            id=doc.id
        )
        return artifact


class RelationBuilder:

    def __init__(self, storage):
        self.storage = storage
        self.relation_repo = RelationRepository(storage)

    def create_relations(self, doc: KnowledgeDocument, all_docs: List[KnowledgeDocument]) -> List[Relation]:
        """
        Maps document references to structural "links_to" or "redirects_to" relationships between stable Artifact IDs.
        """
        relations = []
        for ref in doc.references:
            rel_type = "redirects_to" if ref.reference_type == "redirects_to" else "links_to"
            # Create the relation in storage
            rel = self.relation_repo.create(
                source_id=doc.id,
                target_id=ref.target_document,
                relation_type=rel_type,
                metadata={"weight": 1.0, "source_anchor": ref.source_anchor, "target_anchor": ref.target_anchor}
            )
            relations.append(rel)
        return relations


class ChunkBuilder:

    def __init__(self, storage):
        self.storage = storage
        self.chunk_repo = ChunkRepository(storage)
        self.relation_repo = RelationRepository(storage)

    def create_chunks(self, artifact_id: str, sections: List[Section]) -> List[Chunk]:
        """
        Segments sections of a document into retrieval-sized chunks using the paragraph-first strategy.
        """
        from graphyra.ingestion.chunking import ParagraphChunker
        from graphyra.ingestion.features import ChunkFeatureExtractor
        chunker = ParagraphChunker()
        chunk_dicts = chunker.chunk_document(sections)

        chunks = []
        for c_dict in chunk_dicts:
            txt = c_dict["content"]
            sec_id = c_dict["section_id"]
            
            # Compute baseline structural features
            features = ChunkFeatureExtractor.extract_features(txt, {"heading_depth": 0, "block_depth": 0})
            
            # Create Chunk
            chunk = self.chunk_repo.create(
                artifact_id=artifact_id,
                content=txt,
                metadata={"section_id": sec_id, "length": len(txt), "features": features.to_dict()}
            )
            chunks.append(chunk)

            # Add 'contains' relation in storage
            self.relation_repo.create(
                source_id=artifact_id,
                target_id=chunk.id,
                relation_type="contains"
            )
        return chunks

    def generate_embeddings(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Generates vector embeddings for chunks (V1 implementation is decoupled and runs LLM-free, leaving embeddings as None).
        """
        for chunk in chunks:
            chunk.embedding = None
        return chunks


class IndexBuilder:

    def __init__(self, storage):
        self.storage = storage

    def build_indexes(self):
        """
        Builds SQLite indexing structures.
        """
        if hasattr(self.storage, "analyze_database"):
            self.storage.analyze_database()

    def refresh_indexes(self):
        """
        Refreshes FTS indexes or database tables.
        """
        self.build_indexes()
