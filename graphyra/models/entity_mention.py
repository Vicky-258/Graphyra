from dataclasses import dataclass


@dataclass
class EntityMention:
    entity_id: str
    chunk_id: str