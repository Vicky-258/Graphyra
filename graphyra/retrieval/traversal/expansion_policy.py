from abc import ABC, abstractmethod
from graphyra.models.traversal_models import TraversedRelation, NodeType


class ExpansionPolicy(ABC):

    @abstractmethod
    def expand(self, current_node: str, neighbors: list[TraversedRelation]) -> list[TraversedRelation]:
        """
        Determines which neighbors of the current node are allowed to enter the frontier.
        """
        pass


class DefaultExpansionPolicy(ExpansionPolicy):

    def __init__(self, entity_expansion_limit: int | None, chunk_expansion_limit: int | None, graph_repo):
        self.entity_expansion_limit = entity_expansion_limit
        self.chunk_expansion_limit = chunk_expansion_limit
        self.graph_repo = graph_repo

    def expand(self, current_node: str, neighbors: list[TraversedRelation]) -> list[TraversedRelation]:
        node_type = self.graph_repo.get_node_type(current_node)
        limit = self.entity_expansion_limit if node_type == NodeType.ENTITY else self.chunk_expansion_limit
        if limit is None:
            return neighbors

        # Deterministically sort to preserve stable path traversals before slicing
        sorted_neighbors = sorted(neighbors, key=lambda r: (r.relation_type, r.source, r.target))
        return sorted_neighbors[:limit]
