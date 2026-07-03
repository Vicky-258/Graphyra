from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Relation:
    id: str
    source_id: str
    target_id: str
    relation_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)