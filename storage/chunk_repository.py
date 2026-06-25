import json
from models.chunk import Chunk


class ChunkRepository:

    def __init__(self, storage):
        self.storage = storage

    def create(
        self,
        artifact_id: str,
        content: str,
        metadata: dict | None = None
    ) -> Chunk:
        metadata = metadata or {}
        chunk_id = self.storage.generate_id("chunks", "CHK")

        chunk = Chunk(
            id=chunk_id,
            artifact_id=artifact_id,
            content=content,
            metadata=metadata
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chunks (
                    id,
                    artifact_id,
                    content,
                    metadata
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.artifact_id,
                    chunk.content,
                    json.dumps(chunk.metadata)
                )
            )
            conn.commit()

        return chunk

    def get(self, chunk_id: str) -> Chunk | None:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    artifact_id,
                    content,
                    metadata
                FROM chunks
                WHERE id = ?
                """,
                (chunk_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_chunk(row)

    def get_by_artifact(self, artifact_id: str) -> list[Chunk]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    artifact_id,
                    content,
                    metadata
                FROM chunks
                WHERE artifact_id = ?
                """,
                (artifact_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def list_all(self) -> list[Chunk]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    artifact_id,
                    content,
                    metadata
                FROM chunks
                """
            )
            rows = cursor.fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def _row_to_chunk(self, row) -> Chunk:
        if row is None:
            return None
        return Chunk(
            id=row[0],
            artifact_id=row[1],
            content=row[2],
            metadata=json.loads(row[3] or "{}")
        )
