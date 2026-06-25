from abc import ABC, abstractmethod
from typing import List, Optional
from contracts.models import KnowledgeDocument


class SourceAdapter(ABC):
    """
    Abstract base class defining the contract for all Graphyra Source Adapters.
    An adapter is responsible for source discovery, content fetching, change detection,
    and producing a normalized list of KnowledgeDocuments.
    """

    @abstractmethod
    def ingest(self, state_cache: Optional[dict] = None) -> List[KnowledgeDocument]:
        """
        Ingest content from the external source, returning a list of KnowledgeDocuments.
        Optionally accepts a state_cache dictionary (e.g., listing previously ingested page IDs
        and revision IDs) to support change detection and incremental updates.
        """
        pass
