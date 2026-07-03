from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class Chunk:
    id: str
    artifact_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)