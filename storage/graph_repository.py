import json
from abc import ABC, abstractmethod
from models.traversal_models import TraversedRelation


class GraphRepository(ABC):

    @abstractmethod
    def get_neighbors(self, entity_id: str) -> list[TraversedRelation]:
        """
        Retrieves all relationships starting or ending at the specified entity/anchor ID.
        """
        pass


class SQLiteGraphRepository(GraphRepository):

    def __init__(self, storage):
        self.storage = storage

    def get_neighbors(self, entity_id: str) -> list[TraversedRelation]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_id, target_id, relation_type, metadata
                FROM relations
                WHERE source_id = ? OR target_id = ?
                """,
                (entity_id, entity_id)
            )
            rows = cursor.fetchall()

            neighbors = []
            for src, tgt, rel_type, meta_str in rows:
                meta = {}
                try:
                    if meta_str:
                        meta = json.loads(meta_str)
                except Exception:
                    pass
                
                # Retrieve relationship score/weight from metadata if available
                score = float(meta.get("weight", 1.0))
                
                neighbors.append(TraversedRelation(
                    source=src,
                    target=tgt,
                    relation_type=rel_type,
                    score=score
                ))
            return neighbors
