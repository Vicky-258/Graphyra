import sqlite3
from graphyra.models.evidence_reference import EvidenceReference


class EvidenceRepository:

    def __init__(self, storage):
        self.storage = storage

    def create(
        self,
        artifact_id: str,
        chunk_id: str,
        extraction_method: str,
        confidence: float,
        timestamp: str,
        entity_id: str | None = None,
        relation_id: str | None = None,
        id: str | None = None
    ) -> EvidenceReference:
        evidence_id = id or self.storage.generate_id("evidence_references", "EVI")

        evidence = EvidenceReference(
            id=evidence_id,
            artifact_id=artifact_id,
            chunk_id=chunk_id,
            extraction_method=extraction_method,
            confidence=confidence,
            timestamp=timestamp,
            entity_id=entity_id,
            relation_id=relation_id
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evidence_references (
                    id,
                    artifact_id,
                    chunk_id,
                    extraction_method,
                    confidence,
                    timestamp,
                    entity_id,
                    relation_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.id,
                    evidence.artifact_id,
                    evidence.chunk_id,
                    evidence.extraction_method,
                    evidence.confidence,
                    evidence.timestamp,
                    evidence.entity_id,
                    evidence.relation_id
                )
            )
            conn.commit()

        return evidence

    def get(self, evidence_id: str) -> EvidenceReference | None:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    artifact_id,
                    chunk_id,
                    extraction_method,
                    confidence,
                    timestamp,
                    entity_id,
                    relation_id
                FROM evidence_references
                WHERE id = ?
                """,
                (evidence_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_evidence(row)

    def get_evidence(
        self,
        entity_id: str | None = None,
        relation_id: str | None = None
    ) -> list[EvidenceReference]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            if entity_id and relation_id:
                cursor.execute(
                    """
                    SELECT
                        id,
                        artifact_id,
                        chunk_id,
                        extraction_method,
                        confidence,
                        timestamp,
                        entity_id,
                        relation_id
                    FROM evidence_references
                    WHERE entity_id = ? AND relation_id = ?
                    """,
                    (entity_id, relation_id)
                )
            elif entity_id:
                cursor.execute(
                    """
                    SELECT
                        id,
                        artifact_id,
                        chunk_id,
                        extraction_method,
                        confidence,
                        timestamp,
                        entity_id,
                        relation_id
                    FROM evidence_references
                    WHERE entity_id = ?
                    """,
                    (entity_id,)
                )
            elif relation_id:
                cursor.execute(
                    """
                    SELECT
                        id,
                        artifact_id,
                        chunk_id,
                        extraction_method,
                        confidence,
                        timestamp,
                        entity_id,
                        relation_id
                    FROM evidence_references
                    WHERE relation_id = ?
                    """,
                    (relation_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        artifact_id,
                        chunk_id,
                        extraction_method,
                        confidence,
                        timestamp,
                        entity_id,
                        relation_id
                    FROM evidence_references
                    """
                )
            rows = cursor.fetchall()
            return [self._row_to_evidence(row) for row in rows]

    def _row_to_evidence(self, row) -> EvidenceReference:
        if row is None:
            return None
        return EvidenceReference(
            id=row[0],
            artifact_id=row[1],
            chunk_id=row[2],
            extraction_method=row[3],
            confidence=row[4],
            timestamp=row[5],
            entity_id=row[6],
            relation_id=row[7]
        )
