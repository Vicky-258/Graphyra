from graphyra.models.alias import Alias
from graphyra.storage.alias_repository import AliasRepository
from graphyra.storage.entity_repository import EntityRepository


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

    def list_all(self):
        """Retrieve all aliases in bulk."""
        return self.alias_repo.list_all()

    def get_vocabulary(self) -> set[str]:
        """Get the cached vocabulary of canonical names and aliases."""
        if not hasattr(self, "_cached_vocab") or self._cached_vocab is None:
            names = [e.canonical_name for e in self.entity_repo.list_all()]
            aliases = [a.alias for a in self.list_all()]
            self._cached_vocab = set(names + aliases)
        return self._cached_vocab

    def get_lookup_maps(self) -> tuple[dict[str, str], dict[str, list[str]]]:
        """
        Builds dual O(1) lookup maps:
        - alias_to_entity: lowercase alias string -> entity ID
        - entity_to_aliases: entity ID -> list of alias strings
        """
        all_aliases = self.list_all()
        alias_to_entity = {}
        entity_to_aliases = {}
        for a in all_aliases:
            if a.entity_id not in entity_to_aliases:
                entity_to_aliases[a.entity_id] = []
            entity_to_aliases[a.entity_id].append(a.alias)
            alias_to_entity[a.alias.lower()] = a.entity_id
        return alias_to_entity, entity_to_aliases

