import json
from abc import ABC, abstractmethod
from graphyra.models.traversal_models import TraversedRelation, NodeType


class GraphRepository(ABC):

    @abstractmethod
    def get_neighbors(self, entity_id: str) -> list[TraversedRelation]:
        """
        Retrieves all relationships starting or ending at the specified entity/anchor ID.
        """
        pass

    @abstractmethod
    def get_node_type(self, node_id: str) -> NodeType:
        """
        Retrieves the node type of the specified node ID.
        """
        pass

    @abstractmethod
    def get_all_degrees(self) -> dict[str, int]:
        """
        Precomputes and returns a dictionary of node degrees for all nodes in the relations table.
        """
        pass


class SQLiteGraphRepository(GraphRepository):

    def __init__(self, storage, use_cache: bool = True):
        self.storage = storage
        self.use_cache = use_cache
        self.adjacency_cache = {}
        self.node_type_cache = {}
        self.sql_query_count = 0
        self.warmed_up = False

    def warm_up(self):
        self.adjacency_cache.clear()
        self.node_type_cache.clear()
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT source_id, target_id, relation_type, metadata FROM relations")
                rows = cursor.fetchall()
                self.sql_query_count += 1

                for src, tgt, rel_type, meta_str in rows:
                    meta = {}
                    try:
                        if meta_str:
                            meta = json.loads(meta_str)
                    except Exception:
                        pass
                    score = float(meta.get("weight", 1.0))

                    rel = TraversedRelation(
                        source=src,
                        target=tgt,
                        relation_type=rel_type,
                        score=score
                    )

                    if src not in self.adjacency_cache:
                        self.adjacency_cache[src] = []
                    self.adjacency_cache[src].append(rel)

                    if tgt not in self.adjacency_cache:
                        self.adjacency_cache[tgt] = []
                    self.adjacency_cache[tgt].append(rel)

                    self._cache_node_type(src)
                    self._cache_node_type(tgt)
            self.warmed_up = True
        except Exception:
            pass

    def get_all_degrees(self) -> dict[str, int]:
        degrees = {}
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_id, target_id FROM relations")
            for src, tgt in cursor.fetchall():
                degrees[src] = degrees.get(src, 0) + 1
                degrees[tgt] = degrees.get(tgt, 0) + 1
        return degrees

    def _cache_node_type(self, node_id: str):
        if node_id not in self.node_type_cache:
            if node_id.startswith("ENT_"):
                self.node_type_cache[node_id] = NodeType.ENTITY
            elif node_id.startswith("CHK_"):
                self.node_type_cache[node_id] = NodeType.CHUNK
            elif node_id.startswith("ART_"):
                self.node_type_cache[node_id] = NodeType.ARTIFACT
            else:
                self.node_type_cache[node_id] = NodeType.UNKNOWN

    def get_neighbors(self, entity_id: str) -> list[TraversedRelation]:
        if self.use_cache:
            if not self.warmed_up:
                self.warm_up()
            return self.adjacency_cache.get(entity_id, [])

        self.sql_query_count += 1
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

    def get_node_type(self, node_id: str) -> NodeType:
        # Technical Debt: Node type checking belongs to NodeRepository or KnowledgeRepository,
        # placed here for traversal architecture consistency.
        if self.use_cache:
            if node_id not in self.node_type_cache:
                self._cache_node_type(node_id)
            return self.node_type_cache[node_id]

        if node_id.startswith("ENT_"):
            return NodeType.ENTITY
        elif node_id.startswith("CHK_"):
            return NodeType.CHUNK
        elif node_id.startswith("ART_"):
            return NodeType.ARTIFACT
        return NodeType.UNKNOWN
