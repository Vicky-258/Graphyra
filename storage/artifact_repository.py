import json
from models.artifact import Artifact


class ArtifactRepository:

    def __init__(self, storage):
        self.storage = storage

    def create(
        self,
        title: str,
        source_type: str,
        source: str | None = None,
        metadata: dict | None = None
    ) -> Artifact:
        metadata = metadata or {}
        artifact_id = self.storage.generate_id("artifacts", "ART")

        artifact = Artifact(
            id=artifact_id,
            title=title,
            source_type=source_type,
            source=source,
            metadata=metadata
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO artifacts (
                    id,
                    title,
                    source_type,
                    source,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.title,
                    artifact.source_type,
                    artifact.source,
                    json.dumps(artifact.metadata)
                )
            )
            conn.commit()

        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    source_type,
                    source,
                    metadata
                FROM artifacts
                WHERE id = ?
                """,
                (artifact_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_artifact(row)

    def list_all(self) -> list[Artifact]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    title,
                    source_type,
                    source,
                    metadata
                FROM artifacts
                """
            )
            rows = cursor.fetchall()
            return [self._row_to_artifact(row) for row in rows]

    def _row_to_artifact(self, row) -> Artifact:
        if row is None:
            return None
        return Artifact(
            id=row[0],
            title=row[1],
            source_type=row[2],
            source=row[3],
            metadata=json.loads(row[4] or "{}")
        )

    def delete(self, artifact_id: str) -> bool:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM artifacts WHERE id = ?",
                (artifact_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
