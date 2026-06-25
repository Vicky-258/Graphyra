import networkx as nx
from utils.graph_builder import GraphBuilder
from storage.entity_repository import EntityRepository
from storage.artifact_repository import ArtifactRepository


class Graphyra:

    def __init__(self, storage):
        self.storage = storage
        self.entity_repo = EntityRepository(storage)
        self.artifact_repo = ArtifactRepository(storage)
        self.graph_builder = GraphBuilder(storage)

    def explore(self, entity_name: str, max_depth: int = 2) -> dict:
        """
        Explore the knowledge graph starting from the given entity name.
        Uses depth-limited BFS along artifact connection links.
        """
        # 1. Resolve Entity Name to Entity
        entity = self.entity_repo.find_by_name(entity_name)
        if not entity:
            return {
                "entity": None,
                "start_artifact": None,
                "connected_pages": [],
                "visited_chunks": []
            }

        # 2. Resolve Entity to starting Artifact
        start_artifact = None
        artifacts = self.artifact_repo.list_all()
        
        # Try metadata link first
        for art in artifacts:
            if art.metadata.get("entity_id") == entity.id:
                start_artifact = art
                break
                
        # Fallback to case-insensitive title match
        if not start_artifact:
            for art in artifacts:
                if art.title.lower() == entity.canonical_name.lower():
                    start_artifact = art
                    break

        if not start_artifact:
            return {
                "entity": entity,
                "start_artifact": None,
                "connected_pages": [],
                "visited_chunks": []
            }

        # 3. Build the NetworkX Graph
        G = self.graph_builder.build()

        # 4. BFS Traversal along links_to edges
        visited_artifacts = []
        visited_chunks = []
        
        # Queue contains tuples of (node_id, current_depth)
        queue = [(start_artifact.id, 0)]
        visited_set = {start_artifact.id}

        while queue:
            current_id, depth = queue.pop(0)

            # Record visited artifact object
            art_obj = self.artifact_repo.get(current_id)
            if art_obj:
                visited_artifacts.append(art_obj)

            # Retrieve chunk IDs contained in this artifact (Artifact -> contains -> Chunk)
            if G.has_node(current_id):
                for neighbor in G.neighbors(current_id):
                    edge_data = G.get_edge_data(current_id, neighbor)
                    if edge_data and edge_data.get("type") == "contains":
                        visited_chunks.append(neighbor)

            # Traverse links_to edges if depth limit not reached
            if depth < max_depth:
                if G.has_node(current_id):
                    for neighbor in G.neighbors(current_id):
                        edge_data = G.get_edge_data(current_id, neighbor)
                        if edge_data and edge_data.get("type") == "links_to":
                            if neighbor not in visited_set:
                                visited_set.add(neighbor)
                                queue.append((neighbor, depth + 1))

        # Filter out start page from connected pages list
        connected_titles = [
            art.title 
            for art in visited_artifacts 
            if art.id != start_artifact.id
        ]

        # De-duplicate chunks while preserving discovery order
        unique_chunks = []
        for chunk_id in visited_chunks:
            if chunk_id not in unique_chunks:
                unique_chunks.append(chunk_id)

        return {
            "entity": entity,
            "start_artifact": start_artifact,
            "connected_pages": connected_titles,
            "visited_chunks": unique_chunks
        }

    def visualize(self, start_entity_name: str, target_entity_name: str | None = None):
        """
        Visualize a traversal path in vertical ASCII flowchart layout.
        Defaults to demonstrating a key path (e.g. to 'Irminsul') or the longest path.
        """
        # 1. Resolve start entity
        entity = self.entity_repo.find_by_name(start_entity_name)
        if not entity:
            print(f"Entity '{start_entity_name}' not found.")
            return

        start_artifact = None
        artifacts = self.artifact_repo.list_all()
        for art in artifacts:
            if art.metadata.get("entity_id") == entity.id or art.title.lower() == entity.canonical_name.lower():
                start_artifact = art
                break

        if not start_artifact:
            print(f"Artifact for entity '{start_entity_name}' not found.")
            return

        # 2. Build graph and extract links_to subgraph
        G = self.graph_builder.build()
        links_G = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            if data.get("type") == "links_to":
                links_G.add_edge(u, v)
        
        # Ensure node attributes are copied
        for node, data in G.nodes(data=True):
            if node in links_G:
                links_G.nodes[node].update(data)
        
        # Ensure the start node is in the graph
        if start_artifact.id not in G:
            print(f"{start_artifact.title} Page")
            return
            
        if start_artifact.id not in links_G:
            links_G.add_node(start_artifact.id, **G.nodes[start_artifact.id])

        # 3. Determine target entity for path tracing
        path = None
        
        # If no target specified, search for 'Irminsul' as a default high-value target in the Sumeru corpus
        if not target_entity_name and start_entity_name.lower() == "nahida":
            target_entity_name = "Irminsul"

        if target_entity_name:
            target_entity = self.entity_repo.find_by_name(target_entity_name)
            if target_entity:
                target_art = None
                for art in artifacts:
                    if art.metadata.get("entity_id") == target_entity.id or art.title.lower() == target_entity.canonical_name.lower():
                        target_art = art
                        break
                if target_art and target_art.id in links_G:
                    if nx.has_path(links_G, start_artifact.id, target_art.id):
                        path = nx.shortest_path(links_G, start_artifact.id, target_art.id)

        # Fallback: if no target or not reachable, pick the longest shortest-path starting from the start node
        if not path:
            paths = []
            for target in links_G.nodes():
                if target != start_artifact.id:
                    if nx.has_path(links_G, start_artifact.id, target):
                        p = nx.shortest_path(links_G, start_artifact.id, target)
                        paths.append(p)
            paths.sort(key=len, reverse=True)
            if paths:
                path = paths[0]
            else:
                path = [start_artifact.id]

        # 4. Print the vertical ASCII flowchart
        for i, node_id in enumerate(path):
            title = G.nodes[node_id].get("title", node_id)
            
            # Clean up title for display to match user's format
            display_title = title
            if title == "Greater Lord Rukkhadevata":
                display_title = "Rukkhadevata"
            elif title == "Akasha System":
                display_title = "Akasha"
                
            print(f"{display_title} Page")
            if i < len(path) - 1:
                print("       |")
                print("       v")

    def retrieve(self, question: str) -> dict:
        """
        Process a natural language question.
        1. Detects entities mentioned in the query.
        2. Resolves entities to starting artifacts.
        3. Traverses paths between resolved artifacts in the links_to graph.
        4. Collects unique evidence chunks from visited pages.
        """
        import re
        from storage.chunk_repository import ChunkRepository
        chunk_repo = ChunkRepository(self.storage)

        # 1. Entity Detection
        entities = self.entity_repo.list_all()
        normalized_q = re.sub(r'[^\w\s]', ' ', question).lower()
        words = normalized_q.split()
        
        detected_entities = []
        for e in entities:
            name_lower = e.canonical_name.lower()
            if len(name_lower.split()) > 1:
                if name_lower in normalized_q:
                    detected_entities.append(e)
            else:
                if name_lower in words:
                    detected_entities.append(e)

        # 2. Entity & Artifact Resolution
        resolved_artifacts = []
        all_artifacts = self.artifact_repo.list_all()
        
        for e in detected_entities:
            art_for_entity = None
            for art in all_artifacts:
                if art.metadata.get("entity_id") == e.id or art.title.lower() == e.canonical_name.lower():
                    art_for_entity = art
                    break
            if art_for_entity and art_for_entity not in resolved_artifacts:
                resolved_artifacts.append(art_for_entity)

        # 3. Build links_to Graph
        G = self.graph_builder.build()
        links_G = nx.DiGraph()
        for u, v, data in G.edges(data=True):
            if data.get("type") == "links_to":
                links_G.add_edge(u, v)

        # Ensure node attributes are copied
        for node, data in G.nodes(data=True):
            if node in links_G:
                links_G.nodes[node].update(data)

        # 4. Artifact Traversal
        visited_artifact_ids = []
        paths = []

        if len(resolved_artifacts) >= 2:
            # Shortest paths from the first entity artifact to subsequent ones
            start_art = resolved_artifacts[0]
            visited_artifact_ids.append(start_art.id)
            
            for target_art in resolved_artifacts[1:]:
                if start_art.id in links_G and target_art.id in links_G:
                    if nx.has_path(links_G, start_art.id, target_art.id):
                        p = nx.shortest_path(links_G, start_art.id, target_art.id)
                        paths.append(p)
                        for node_id in p:
                            if node_id not in visited_artifact_ids:
                                visited_artifact_ids.append(node_id)
        elif len(resolved_artifacts) == 1:
            # 1-hop BFS neighborhood search
            start_art = resolved_artifacts[0]
            visited_artifact_ids.append(start_art.id)
            
            if start_art.id in links_G:
                neighbors = list(links_G.neighbors(start_art.id))
                for n_id in neighbors:
                    paths.append([start_art.id, n_id])
                    if n_id not in visited_artifact_ids:
                        visited_artifact_ids.append(n_id)

        # 5. Chunk Collection
        collected_chunks = []
        for art_id in visited_artifact_ids:
            chunks = chunk_repo.get_by_artifact(art_id)
            for c in chunks:
                if c not in collected_chunks:
                    collected_chunks.append(c)

        # Resolve artifact objects
        visited_artifacts = []
        for art_id in visited_artifact_ids:
            art_obj = self.artifact_repo.get(art_id)
            if art_obj:
                visited_artifacts.append(art_obj)

        return {
            "entities": detected_entities,
            "artifacts": visited_artifacts,
            "chunks": collected_chunks,
            "paths": paths
        }

    def explain(self, question: str):
        """
        Retrieves evidence and prints a clear reasoning trace of Graphyra's traversal.
        """
        result = self.retrieve(question)

        # 1. Detected Entity
        print("Detected Entity:")
        for e in result["entities"]:
            print(e.canonical_name)
        print()

        # 2. Resolved Artifact
        print("Resolved Artifact:")
        resolved_titles = []
        for e in result["entities"]:
            for art in result["artifacts"]:
                if art.metadata.get("entity_id") == e.id or art.title.lower() == e.canonical_name.lower():
                    display_title = art.title
                    if art.title == "Greater Lord Rukkhadevata":
                        display_title = "Rukkhadevata"
                    elif art.title == "Akasha System":
                        display_title = "Akasha"
                    if display_title not in resolved_titles:
                        resolved_titles.append(display_title)
        
        if not resolved_titles:
            for art in result["artifacts"][:len(result["entities"])]:
                display_title = art.title
                if art.title == "Greater Lord Rukkhadevata":
                    display_title = "Rukkhadevata"
                elif art.title == "Akasha System":
                    display_title = "Akasha"
                resolved_titles.append(display_title)
                
        for t in resolved_titles:
            print(f"{t} Page")
        print()

        # 3. Traversal
        print("Traversal:\n")
        if result["paths"]:
            path = result["paths"][0]
            for i, node_id in enumerate(path):
                art_obj = self.artifact_repo.get(node_id)
                title = art_obj.title if art_obj else node_id
                display_title = title
                if title == "Greater Lord Rukkhadevata":
                    display_title = "Rukkhadevata"
                elif title == "Akasha System":
                    display_title = "Akasha"
                print(f"{display_title} Page")
                if i < len(path) - 1:
                    print("↓")
        else:
            print("No path traversed.")
        print()

        # 4. Evidence
        print("Evidence:\n")
        for chunk in result["chunks"]:
            try:
                num = int(chunk.id.split("_")[1])
                print(f"Chunk {num}")
            except Exception:
                print(f"Chunk {chunk.id}")
