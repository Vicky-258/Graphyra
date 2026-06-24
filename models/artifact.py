from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Artifact:
    id: str
    title: str
    source_type: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)