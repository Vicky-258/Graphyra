import sqlite3


class SQLiteStorage:

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

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

            conn.commit()

    def generate_id(self, table_name: str, prefix: str):

        with self.get_connection() as conn:

            cursor = conn.cursor()

            cursor.execute(
                f"""
                SELECT id
                FROM {table_name}
                WHERE id LIKE '{prefix}_%'
                ORDER BY id DESC
                LIMIT 1
                """
            )

            row = cursor.fetchone()

            if row is None:
                next_number = 1
            else:
                last_id = row[0]
                next_number = int(last_id.split("_")[1]) + 1

            return f"{prefix}_{next_number:03d}"