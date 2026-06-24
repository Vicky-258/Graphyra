import json

from models.entity import Entity
from utils.entity_type import EntityType


class EntityRepository:

    def __init__(self, storage):
        self.storage = storage

    def create(
        self,
        canonical_name: str,
        entity_type: EntityType,
        metadata: dict | None = None
    ):

        metadata = metadata or {}

        entity_id = self.storage.generate_id(
            "entities",
            "ENT"
        )

        entity = Entity(
            id=entity_id,
            canonical_name=canonical_name,
            entity_type=entity_type,
            metadata=metadata
        )

        with self.storage.get_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO entities (
                    id,
                    canonical_name,
                    entity_type,
                    metadata
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.canonical_name,
                    entity.entity_type.value,
                    json.dumps(entity.metadata)
                )
            )

            conn.commit()

        return entity

    def get(self, entity_id: str):

        with self.storage.get_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    canonical_name,
                    entity_type,
                    metadata
                FROM entities
                WHERE id = ?
                """,
                (entity_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return Entity(
                id=row[0],
                canonical_name=row[1],
                entity_type=EntityType(row[2]),
                metadata=json.loads(row[3] or "{}")
            )

    def find_by_name(self, name: str):

        with self.storage.get_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    canonical_name,
                    entity_type,
                    metadata
                FROM entities
                WHERE LOWER(canonical_name)=LOWER(?)
                """,
                (name,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return Entity(
                id=row[0],
                canonical_name=row[1],
                entity_type=EntityType(row[2]),
                metadata=json.loads(row[3] or "{}")
            )