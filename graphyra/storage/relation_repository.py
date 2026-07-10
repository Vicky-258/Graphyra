import json
from graphyra.models.relation import Relation


class RelationRepository:

    def __init__(self, storage):
        self.storage = storage

    def create(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        metadata: dict | None = None,
        id: str | None = None
    ) -> Relation:
        metadata = metadata or {}
        relation_id = id or self.storage.generate_id("relations", "REL")

        relation = Relation(
            id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            metadata=metadata
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO relations (
                    id,
                    source_id,
                    target_id,
                    relation_type,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    relation.id,
                    relation.source_id,
                    relation.target_id,
                    relation.relation_type,
                    json.dumps(relation.metadata)
                )
            )
            conn.commit()

        return relation

    def get(self, relation_id: str) -> Relation | None:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    source_id,
                    target_id,
                    relation_type,
                    metadata
                FROM relations
                WHERE id = ?
                """,
                (relation_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_relation(row)

    def get_relations(self, source_id: str | None = None) -> list[Relation]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            if source_id:
                cursor.execute(
                    """
                    SELECT
                        id,
                        source_id,
                        target_id,
                        relation_type,
                        metadata
                    FROM relations
                    WHERE source_id = ?
                    """,
                    (source_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        source_id,
                        target_id,
                        relation_type,
                        metadata
                    FROM relations
                    """
                )
            rows = cursor.fetchall()
            return [self._row_to_relation(row) for row in rows]

    def list_all(self) -> list[Relation]:
        return self.get_relations()

    def _row_to_relation(self, row) -> Relation:
        if row is None:
            return None
        return Relation(
            id=row[0],
            source_id=row[1],
            target_id=row[2],
            relation_type=row[3],
            metadata=json.loads(row[4] or "{}")
        )

    def delete(self, relation_id: str) -> bool:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM relations WHERE id = ?",
                (relation_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_by_node(self, node_id: str) -> bool:
        """Delete all relations where the specified node is source or target."""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM relations WHERE source_id = ? OR target_id = ?",
                (node_id, node_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_connected_nodes(self, node_id: str) -> list[str]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_id, target_id
                FROM relations
                WHERE source_id = ? OR target_id = ?
                """,
                (node_id, node_id)
            )
            rows = cursor.fetchall()
            connected = set()
            for src, tgt in rows:
                if src == node_id:
                    connected.add(tgt)
                else:
                    connected.add(src)
            return list(connected)
