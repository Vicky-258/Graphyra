import json
from typing import Optional, List
from graphyra.models.chunk import Chunk


class ChunkRepository:

    def __init__(self, storage):
        self.storage = storage

    def create(
        self,
        artifact_id: str,
        content: str,
        metadata: dict | None = None,
        id: str | None = None,
        embedding: list[float] | None = None
    ) -> Chunk:
        metadata = metadata or {}
        chunk_id = id or self.storage.generate_id("chunks", "CHK")

        chunk = Chunk(
            id=chunk_id,
            artifact_id=artifact_id,
            content=content,
            embedding=embedding,
            metadata=metadata
        )

        embedding_str = json.dumps(embedding) if embedding is not None else None

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chunks (
                    id,
                    artifact_id,
                    content,
                    embedding,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chunk.id,
                    chunk.artifact_id,
                    chunk.content,
                    embedding_str,
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
                    embedding,
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
                    embedding,
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
                    embedding,
                    metadata
                FROM chunks
                """
            )
            rows = cursor.fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def _row_to_chunk(self, row) -> Chunk:
        if row is None:
            return None
        emb = None
        if row[3] is not None:
            emb = json.loads(row[3])
        return Chunk(
            id=row[0],
            artifact_id=row[1],
            content=row[2],
            embedding=emb,
            metadata=json.loads(row[4] or "{}")
        )

    def update_embedding(self, chunk_id: str, embedding: list[float] | None) -> None:
        """Updates the embedding array of a specific chunk."""
        import json
        embedding_str = json.dumps(embedding) if embedding is not None else None
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE chunks SET embedding = ? WHERE id = ?",
                (embedding_str, chunk_id)
            )
            conn.commit()


