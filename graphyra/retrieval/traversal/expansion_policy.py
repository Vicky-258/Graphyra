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

    def __init__(self, graph_repo):
        self.graph_repo = graph_repo

    def order_neighbors(self, neighbors: list[TraversedRelation]) -> list[TraversedRelation]:
        """
        Deterministically orders neighbors by relation weight (score descending)
        and breaks ties using properties to preserve stable path traversals.
        """
        return sorted(neighbors, key=lambda r: (-r.score, r.relation_type, r.source, r.target))

    def expand(self, current_node: str, neighbors: list[TraversedRelation]) -> list[TraversedRelation]:
        return self.order_neighbors(neighbors)
