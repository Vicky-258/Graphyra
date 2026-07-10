from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional


@dataclass
class ContentBlock:
    type: str
    content: Any


@dataclass
class Section:
    id: str
    title: str
    content_blocks: List[ContentBlock] = field(default_factory=list)


@dataclass
class Reference:
    source_document: str
    source_anchor: str
    target_document: str
    target_anchor: str
    reference_type: str


from enum import Enum

class EntityStrategy(Enum):
    CREATE = "CREATE"
    LINK = "LINK"
    IGNORE = "IGNORE"

class ArtifactStrategy(Enum):
    CREATE = "CREATE"
    IGNORE = "IGNORE"

@dataclass
class IngestionDirectives:
    entity_strategy: EntityStrategy
    artifact_strategy: ArtifactStrategy = ArtifactStrategy.CREATE
    target_anchor: Optional[str] = None

@dataclass
class KnowledgeDocument:
    id: str
    title: str
    source_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Section] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    ingestion_directives: Optional[IngestionDirectives] = None
