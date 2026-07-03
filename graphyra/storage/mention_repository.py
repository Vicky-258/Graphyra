from graphyra.models.entity_mention import EntityMention


class MentionRepository:

    def __init__(self, storage, use_cache: bool = True):
        self.storage = storage
        self.use_cache = use_cache
        self.entity_to_chunks = {}
        self.chunk_to_entities = {}
        self.sql_query_count = 0
        self.warmed_up = False

    def warm_up(self):
        self.entity_to_chunks.clear()
        self.chunk_to_entities.clear()
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT entity_id, chunk_id FROM entity_mentions")
                rows = cursor.fetchall()
                self.sql_query_count += 1

                for ent_id, chunk_id in rows:
                    if ent_id not in self.entity_to_chunks:
                        self.entity_to_chunks[ent_id] = []
                    self.entity_to_chunks[ent_id].append(chunk_id)

                    if chunk_id not in self.chunk_to_entities:
                        self.chunk_to_entities[chunk_id] = []
                    self.chunk_to_entities[chunk_id].append(ent_id)
            self.warmed_up = True
        except Exception:
            pass

    def add(self, entity_id: str, chunk_id: str) -> EntityMention:
        mention = EntityMention(
            entity_id=entity_id,
            chunk_id=chunk_id
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO entity_mentions (
                    entity_id,
                    chunk_id
                )
                VALUES (?, ?)
                """,
                (
                    mention.entity_id,
                    mention.chunk_id
                )
            )
            conn.commit()

        # Update cache if enabled
        if self.use_cache:
            # Note: if warm_up has not run yet, we don't strictly need to do anything since it will load everything anyway, but doing it keeps it correct.
            if self.warmed_up:
                if mention.entity_id not in self.entity_to_chunks:
                    self.entity_to_chunks[mention.entity_id] = []
                if mention.chunk_id not in self.entity_to_chunks[mention.entity_id]:
                    self.entity_to_chunks[mention.entity_id].append(mention.chunk_id)

                if mention.chunk_id not in self.chunk_to_entities:
                    self.chunk_to_entities[mention.chunk_id] = []
                if mention.entity_id not in self.chunk_to_entities[mention.chunk_id]:
                    self.chunk_to_entities[mention.chunk_id].append(mention.entity_id)

        return mention

    def get_chunks_for_entity(self, entity_id: str) -> list[str]:
        if self.use_cache:
            if not self.warmed_up:
                self.warm_up()
            return self.entity_to_chunks.get(entity_id, [])

        self.sql_query_count += 1
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT chunk_id
                FROM entity_mentions
                WHERE entity_id = ?
                """,
                (entity_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_entities_for_chunk(self, chunk_id: str) -> list[str]:
        if self.use_cache:
            return self.chunk_to_entities.get(chunk_id, [])

        self.sql_query_count += 1
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT entity_id
                FROM entity_mentions
                WHERE chunk_id = ?
                """,
                (chunk_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
