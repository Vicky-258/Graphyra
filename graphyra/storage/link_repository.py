from graphyra.models.artifact_link import ArtifactLink


class LinkRepository:

    def __init__(self, storage):
        self.storage = storage

    def add(self, source_artifact_id: str, target_artifact_id: str) -> ArtifactLink:
        link = ArtifactLink(
            source_artifact_id=source_artifact_id,
            target_artifact_id=target_artifact_id
        )

        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO artifact_links (
                    source_artifact_id,
                    target_artifact_id
                )
                VALUES (?, ?)
                """,
                (
                    link.source_artifact_id,
                    link.target_artifact_id
                )
            )
            conn.commit()

        return link

    def get_outbound_links(self, source_artifact_id: str) -> list[str]:
        """Returns the list of target_artifact_ids linked from the source_artifact_id."""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT target_artifact_id
                FROM artifact_links
                WHERE source_artifact_id = ?
                """,
                (source_artifact_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_outgoing_links(self, source_artifact_id: str) -> list[str]:
        """Alias for get_outbound_links."""
        return self.get_outbound_links(source_artifact_id)

    def get_inbound_links(self, target_artifact_id: str) -> list[str]:
        """Returns the list of source_artifact_ids that link to the target_artifact_id."""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_artifact_id
                FROM artifact_links
                WHERE target_artifact_id = ?
                """,
                (target_artifact_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def list_all(self) -> list[ArtifactLink]:
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT source_artifact_id, target_artifact_id
                FROM artifact_links
                """
            )
            rows = cursor.fetchall()
            return [
                ArtifactLink(
                    source_artifact_id=row[0],
                    target_artifact_id=row[1]
                )
                for row in rows
            ]
