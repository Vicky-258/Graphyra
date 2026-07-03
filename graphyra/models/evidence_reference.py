from dataclasses import dataclass
from typing import Optional


@dataclass
class EvidenceReference:
    id: str
    artifact_id: str
    chunk_id: str
    extraction_method: str
    confidence: float
    timestamp: str
    entity_id: Optional[str] = None
    relation_id: Optional[str] = None
