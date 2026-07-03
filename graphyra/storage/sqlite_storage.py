import sqlite3
import json
import threading
from contextlib import contextmanager
from graphyra.storage.knowledge_storage import KnowledgeStorage


class SQLiteConnectionProxy:
    def __init__(self, real_conn):
        self._conn = real_conn
        self._in_bulk = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def commit(self):
        if not self._in_bulk:
            self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)

    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        return self._conn.executemany(*args, **kwargs)

    def real_commit(self):
        self._conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._conn.rollback()
        elif not self._in_bulk:
            self._conn.commit()


class SQLiteStorage(KnowledgeStorage):

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        
        # Import and instantiate repositories to avoid circular dependency at module level
        from graphyra.storage.artifact_repository import ArtifactRepository
        from graphyra.storage.chunk_repository import ChunkRepository
        from graphyra.storage.entity_repository import EntityRepository
        from graphyra.storage.alias_repository import AliasRepository
        from graphyra.storage.mention_repository import MentionRepository
        from graphyra.storage.relation_repository import RelationRepository
        from graphyra.storage.evidence_repository import EvidenceRepository

        self.artifact_repo = ArtifactRepository(self)
        self.chunk_repo = ChunkRepository(self)
        self.entity_repo = EntityRepository(self)
        self.alias_repo = AliasRepository(self)
        self.mention_repo = MentionRepository(self)
        self.relation_repo = RelationRepository(self)
        self.evidence_repo = EvidenceRepository(self)

    def get_connection(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            real_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            real_conn.execute("PRAGMA foreign_keys = ON")
            real_conn.execute("PRAGMA synchronous = OFF")
            real_conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn = SQLiteConnectionProxy(real_conn)
        return self._local.conn

    @contextmanager
    def bulk_transaction(self):
        conn = self.get_connection()
        conn._in_bulk = True
        try:
            yield
            conn.real_commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn._in_bulk = False

    def initialize_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # -------------------------
            # Artifacts
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source TEXT,
                metadata TEXT
            )
            """)

            # -------------------------
            # Chunks
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT,
                metadata TEXT,
                FOREIGN KEY (artifact_id)
                    REFERENCES artifacts(id)
                    ON DELETE CASCADE
            )
            """)

            # -------------------------
            # Entities
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                canonical_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                metadata TEXT
            )
            """)

            # -------------------------
            # Aliases
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                entity_id TEXT NOT NULL,
                alias TEXT NOT NULL,
                FOREIGN KEY (entity_id)
                    REFERENCES entities(id)
                    ON DELETE CASCADE
            )
            """)

            # -------------------------
            # Entity Mentions
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_mentions (
                entity_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                FOREIGN KEY (entity_id)
                    REFERENCES entities(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (chunk_id)
                    REFERENCES chunks(id)
                    ON DELETE CASCADE
            )
            """)

            # -------------------------
            # Relations
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                metadata TEXT
            )
            """)

            # -------------------------
            # Artifact Links
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifact_links (
                source_artifact_id TEXT NOT NULL,
                target_artifact_id TEXT NOT NULL,
                PRIMARY KEY (source_artifact_id, target_artifact_id),
                FOREIGN KEY (source_artifact_id)
                    REFERENCES artifacts(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (target_artifact_id)
                    REFERENCES artifacts(id)
                    ON DELETE CASCADE
            )
            """)

            # -------------------------
            # Evidence References (Provenance)
            # -------------------------
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_references (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                extraction_method TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL,
                entity_id TEXT,
                relation_id TEXT,
                FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (relation_id) REFERENCES relations(id) ON DELETE CASCADE
            )
            """)

            # -------------------------
            # Indexes
            # -------------------------
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alias_entity
            ON aliases(entity_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_entity
            ON entity_mentions(entity_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_mentions_chunk
            ON entity_mentions(chunk_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_artifact_links_source
            ON artifact_links(source_artifact_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_artifact_links_target
            ON artifact_links(target_artifact_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evidence_entity
            ON evidence_references(entity_id)
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_evidence_relation
            ON evidence_references(relation_id)
            """)

            conn.commit()

    def generate_id(self, table_name: str, prefix: str):
        if not hasattr(self, "_last_ids"):
            self._last_ids = {}
            self._id_lock = threading.Lock()

        with self._id_lock:
            cache_key = (table_name, prefix)
            if cache_key not in self._last_ids:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    prefix_pattern = f"{prefix}_%"
                    prefix_len = len(prefix) + 2  # prefix + underscore + 1 (for 1-based indexing in SUBSTR)
                    cursor.execute(
                        f"""
                        SELECT id
                        FROM {table_name}
                        WHERE id LIKE ?
                        ORDER BY CAST(SUBSTR(id, {prefix_len}) AS INTEGER) DESC
                        LIMIT 1
                        """,
                        (prefix_pattern,)
                    )
                    row = cursor.fetchone()
                    if row is None:
                        last_num = 0
                    else:
                        last_id = row[0]
                        try:
                            last_num = int(last_id.split("_")[1])
                        except (IndexError, ValueError):
                            last_num = 0
                    self._last_ids[cache_key] = last_num

            self._last_ids[cache_key] += 1
            next_number = self._last_ids[cache_key]
            return f"{prefix}_{next_number:03d}"

    def clear_id_cache(self):
        if hasattr(self, "_last_ids"):
            with self._id_lock:
                self._last_ids.clear()

    # ---------- Artifacts ----------

    def create_artifact(self, artifact):
        return self.artifact_repo.create(
            title=artifact.title,
            source_type=artifact.source_type,
            source=artifact.source,
            metadata=artifact.metadata,
            id=artifact.id
        )

    def get_artifact(self, artifact_id):
        return self.artifact_repo.get(artifact_id)

    def list_artifacts(self):
        return self.artifact_repo.list_all()

    # ---------- Chunks ----------

    def create_chunk(self, chunk):
        return self.chunk_repo.create(
            artifact_id=chunk.artifact_id,
            content=chunk.content,
            metadata=chunk.metadata,
            id=chunk.id,
            embedding=chunk.embedding
        )

    def get_chunk(self, chunk_id):
        return self.chunk_repo.get(chunk_id)

    def get_chunks_by_artifact(self, artifact_id):
        return self.chunk_repo.get_by_artifact(artifact_id)

    # ---------- Entities ----------

    def create_entity(self, entity):
        return self.entity_repo.create(
            canonical_name=entity.canonical_name,
            entity_type=entity.entity_type,
            metadata=entity.metadata,
            id=entity.id
        )

    def get_entity(self, entity_id):
        return self.entity_repo.get(entity_id)

    def find_entity_by_name(self, name):
        return self.entity_repo.find_by_name(name)

    # ---------- Aliases ----------

    def add_alias(self, alias):
        return self.alias_repo.add(
            entity_id=alias.entity_id,
            alias=alias.alias
        )

    def get_aliases(self, entity_id):
        return self.alias_repo.get_aliases(entity_id)

    # ---------- Mentions ----------

    def add_mention(self, mention):
        return self.mention_repo.add(
            entity_id=mention.entity_id,
            chunk_id=mention.chunk_id
        )

    def get_chunks_for_entity(self, entity_id):
        return self.mention_repo.get_chunks_for_entity(entity_id)

    def get_entities_for_chunk(self, chunk_id):
        return self.mention_repo.get_entities_for_chunk(chunk_id)

    # ---------- Relations ----------

    def create_relation(self, relation):
        return self.relation_repo.create(
            source_id=relation.source_id,
            target_id=relation.target_id,
            relation_type=relation.relation_type,
            metadata=relation.metadata,
            id=relation.id
        )

    def get_relations(self, source_id=None):
        return self.relation_repo.get_relations(source_id)

    # ---------- Evidence / Provenance ----------

    def add_evidence(self, evidence):
        return self.evidence_repo.create(
            artifact_id=evidence.artifact_id,
            chunk_id=evidence.chunk_id,
            extraction_method=evidence.extraction_method,
            confidence=evidence.confidence,
            timestamp=evidence.timestamp,
            entity_id=evidence.entity_id,
            relation_id=evidence.relation_id,
            id=evidence.id
        )

    def get_evidence(self, entity_id=None, relation_id=None):
        return self.evidence_repo.get_evidence(entity_id, relation_id)