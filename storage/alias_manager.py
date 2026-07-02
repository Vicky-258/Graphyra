from models.alias import Alias
from storage.alias_repository import AliasRepository
from storage.entity_repository import EntityRepository


class AliasManager:

    def __init__(self, storage):
        self.storage = storage
        self.alias_repo = AliasRepository(storage)
        self.entity_repo = EntityRepository(storage)

    def add_alias(self, entity_id: str, alias: str) -> Alias:
        """Add an alias for a given entity."""
        return self.alias_repo.add(entity_id, alias)

    def remove_alias(self, entity_id: str, alias: str) -> bool:
        """Remove a specific alias from a given entity."""
        return self.alias_repo.remove(entity_id, alias)

    def find_by_alias(self, alias: str) -> list[str]:
        """Find entity IDs that have this alias."""
        return self.alias_repo.find_by_alias(alias)

    def get_aliases(self, entity_id: str) -> list[str]:
        """Get all aliases for a given entity."""
        return self.alias_repo.get_aliases(entity_id)

    def canonicalize(self, name: str) -> str:
        """
        Normalize the name and check if it is a known alias or canonical name of an existing entity.
        If it matches an alias, return the canonical name of that entity.
        Otherwise, return a cleaned representation of the original name.
        """
        cleaned_name = " ".join(name.strip().split())
        if not cleaned_name:
            return cleaned_name

        # 1. Check if it's an exact canonical name match
        entity = self.entity_repo.find_by_name(cleaned_name)
        if entity:
            return entity.canonical_name

        # 2. Check if it matches a known alias
        entity_ids = self.alias_repo.find_by_alias(cleaned_name)
        if entity_ids:
            # Return canonical name of the first matching entity
            ent = self.entity_repo.get(entity_ids[0])
            if ent:
                return ent.canonical_name

        return cleaned_name
