import networkx as nx
from storage.entity_repository import EntityRepository
from storage.artifact_repository import ArtifactRepository
from storage.chunk_repository import ChunkRepository
from storage.mention_repository import MentionRepository
from storage.link_repository import LinkRepository


class GraphBuilder:

    def __init__(self, storage):
        self.storage = storage
        self.entity_repo = EntityRepository(storage)
        self.artifact_repo = ArtifactRepository(storage)
        self.chunk_repo = ChunkRepository(storage)
        self.mention_repo = MentionRepository(storage)
        self.link_repo = LinkRepository(storage)

    def build(self) -> nx.DiGraph:
        G = nx.DiGraph()

        # 1. Fetch and Add Node Data
        entities = self.entity_repo.list_all()
        artifacts = self.artifact_repo.list_all()
        chunks = self.chunk_repo.list_all()

        # Add Entities as nodes
        for e in entities:
            G.add_node(
                e.id,
                type="entity",
                canonical_name=e.canonical_name,
                entity_type=e.entity_type.value,
                metadata=e.metadata
            )

        # Add Artifacts as nodes
        for a in artifacts:
            G.add_node(
                a.id,
                type="artifact",
                title=a.title,
                source_type=a.source_type,
                source=a.source,
                metadata=a.metadata
            )

        # Add Chunks as nodes
        for c in chunks:
            G.add_node(
                c.id,
                type="chunk",
                artifact_id=c.artifact_id,
                content=c.content,
                metadata=c.metadata
            )

        # 2. Add Contains Edges (Artifact -> Chunk)
        for c in chunks:
            G.add_edge(c.artifact_id, c.id, type="contains")

        # 3. Add Mentions Edges (Chunk -> Entity)
        # Fetch mentions directly from table to do it in one pass
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT entity_id, chunk_id FROM entity_mentions")
            mentions = cursor.fetchall()
            for entity_id, chunk_id in mentions:
                G.add_edge(chunk_id, entity_id, type="mentions")

        # 4. Add Links Edges (Artifact -> Artifact)
        links = self.link_repo.list_all()
        for link in links:
            G.add_edge(
                link.source_artifact_id,
                link.target_artifact_id,
                type="links_to"
            )

        return G
