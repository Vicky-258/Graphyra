from enum import Enum


class EntityType(Enum):
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    EVENT = "EVENT"
    CONCEPT = "CONCEPT"
    OTHER = "OTHER"