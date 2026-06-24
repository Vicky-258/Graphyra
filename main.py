from storage.sqlite_storage import SQLiteStorage

from storage.entity_repository import EntityRepository

from utils.entity_type import EntityType


storage = SQLiteStorage("graphyra.db")

storage.initialize_database()

entity_repo = EntityRepository(storage)

nahida = entity_repo.create(
    canonical_name="Nahida",
    entity_type=EntityType.PERSON
)

print(nahida)

loaded = entity_repo.get(
    nahida.id
)

print(loaded)

found = entity_repo.find_by_name(
    "Nahida"
)

print(found)