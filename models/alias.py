from dataclasses import dataclass


@dataclass
class Alias:
    entity_id: str
    alias: str