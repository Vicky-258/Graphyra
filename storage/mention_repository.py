from models.entity_mention import EntityMention


class MentionRepository:

    def __init__(self, storage):
        self.storage = storage

    def add(self, entity_id: str, chunk_id: str) -> EntityMention:
        mention = EntityMention(
            entity_id=entity_id,
            chunk_id=chunk_id
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO entity_mentions (
                    entity_id,
                    chunk_id
                )
                VALUES (?, ?)
                """,
                (
                    mention.entity_id,
                    mention.chunk_id
                )
            )
            conn.commit()

        return mention

    def get_chunks_for_entity(self, entity_id: str) -> list[str]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT chunk_id
                FROM entity_mentions
                WHERE entity_id = ?
                """,
                (entity_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_entities_for_chunk(self, chunk_id: str) -> list[str]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT entity_id
                FROM entity_mentions
                WHERE chunk_id = ?
                """,
                (chunk_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
