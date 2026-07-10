import datetime
from typing import List, Tuple
from graphyra.models.entity import Entity
from graphyra.models.chunk import Chunk
from graphyra.utils.entity_type import EntityType
from graphyra.models.evidence_reference import EvidenceReference
from graphyra.storage.anchor_resolver import AnchorResolver
from graphyra.storage.mention_repository import MentionRepository
from graphyra.storage.relation_repository import RelationRepository
from graphyra.ingestion.mention_extractor import MentionExtractor

class AnchorExtractor:
    """
    Day 5 Ingestion Pipeline Component.
    Responsible for extracting anchors and mapping aliases to resolve/persist entity connections.
    """

    def __init__(self, storage, mention_extractor: MentionExtractor):
        self.storage = storage
        self.mention_extractor = mention_extractor
        self.anchor_resolver = AnchorResolver(storage)
        self.mention_repo = MentionRepository(storage)
        self.relation_repo = RelationRepository(storage)

    def extract_anchors(self, chunks: List[Chunk], progress_callback = None) -> Tuple[int, int, int]:
        """
        Runs anchor extraction across all chunks.
        Returns:
            anchors_resolved: Count of new unique anchors created/resolved.
            mentions_extracted: Total mentions mapped in storage.
            relations_created: Count of mentions relations created.
        """
        anchors_resolved = 0
        mentions_extracted = 0
        relations_created = 0

        total_chunks = len(chunks)
        for idx, chunk in enumerate(chunks):
            if idx % 100 == 0 and idx > 0:
                if progress_callback:
                    progress_callback(85.0 + (idx / total_chunks) * 13.0, f"Processed {idx}/{total_chunks} chunks for entity mentions (resolved {anchors_resolved} anchors)...")
                print(f"[Ingestion] Processed {idx}/{total_chunks} chunks for entity mentions (resolved {anchors_resolved} anchors)...")

            extracted_terms = self.mention_extractor.extract_mentions(chunk)
            for term in extracted_terms:
                existing = self.anchor_resolver.resolve(term)
                
                # Resolve or dynamically create the anchor
                anchor = self.resolve_aliases(term)
                if anchor:
                    if not existing:
                        anchors_resolved += 1
                    
                    # Persist mention mapping
                    self.mention_repo.add(entity_id=anchor.id, chunk_id=chunk.id)
                    mentions_extracted += 1
                    
                    # Create EvidenceReference for anchor mention
                    self.storage.add_evidence(EvidenceReference(
                        id="",
                        artifact_id=chunk.artifact_id,
                        chunk_id=chunk.id,
                        extraction_method="pipeline_mention_detection",
                        confidence=1.0,
                        timestamp=datetime.datetime.now().isoformat(),
                        entity_id=anchor.id
                    ))
                    
                    # Store mentions relation
                    rel_obj = self.relation_repo.create(
                        source_id=chunk.id,
                        target_id=anchor.id,
                        relation_type="mentions"
                    )
                    relations_created += 1
                    
                    # Create EvidenceReference for mentions relationship
                    self.storage.add_evidence(EvidenceReference(
                        id="",
                        artifact_id=chunk.artifact_id,
                        chunk_id=chunk.id,
                        extraction_method="pipeline_mention_relation",
                        confidence=1.0,
                        timestamp=datetime.datetime.now().isoformat(),
                        relation_id=rel_obj.id
                    ))

        return anchors_resolved, mentions_extracted, relations_created

    def resolve_aliases(self, term: str) -> Entity:
        """Resolves alias synonyms to their canonical entity anchor."""
        return self.anchor_resolver.resolve(term, create_if_missing=True)
