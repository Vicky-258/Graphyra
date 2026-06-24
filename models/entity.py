from dataclasses import dataclass, field
from typing import Dict, Any

from utils.entity_type import EntityType


@dataclass
class Entity:
    id: str
    canonical_name: str
    entity_type: EntityType
    metadata: Dict[str, Any] = field(default_factory=dict)