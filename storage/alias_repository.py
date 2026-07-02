from models.alias import Alias


class AliasRepository:

    def __init__(self, storage):
        self.storage = storage

    def add(self, entity_id: str, alias: str) -> Alias:
        # Check if the alias already exists for this entity to prevent duplicate key errors if not unique constraint
        # (Though schema says aliases has no primary key, it is clean to avoid duplicate insertion)
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM aliases WHERE entity_id = ? AND alias = ?
                """,
                (entity_id, alias)
            )
            if cursor.fetchone() is not None:
                return Alias(entity_id=entity_id, alias=alias)

            cursor.execute(
                """
                INSERT INTO aliases (
                    entity_id,
                    alias
                )
                VALUES (?, ?)
                """,
                (entity_id, alias)
            )
            conn.commit()

        return Alias(entity_id=entity_id, alias=alias)

    def remove(self, entity_id: str, alias: str) -> bool:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM aliases
                WHERE entity_id = ? AND alias = ?
                """,
                (entity_id, alias)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_aliases(self, entity_id: str) -> list[str]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT alias
                FROM aliases
                WHERE entity_id = ?
                """,
                (entity_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def find_by_alias(self, alias: str) -> list[str]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT entity_id
                FROM aliases
                WHERE LOWER(alias) = LOWER(?)
                """,
                (alias,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
