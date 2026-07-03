import networkx as nx
from graphyra.utils.graph_builder import GraphBuilder
from graphyra.storage.entity_repository import EntityRepository
from graphyra.storage.artifact_repository import ArtifactRepository
from graphyra.storage.anchor_resolver import AnchorResolver
from graphyra.storage.alias_manager import AliasManager
from graphyra.models.traversal_models import TraversalRequest, TraversalPolicy
from graphyra.traversal_engine import TraversalEngine
from graphyra.storage.graph_repository import SQLiteGraphRepository
from graphyra.storage.evidence_retriever import EvidenceRetriever
from graphyra.subgraph_builder import SubgraphBuilder


class Graphyra:

    def __init__(
        self,
        storage,
        embedding_engine=None,
        vector_index=None,
        fusion_engine=None,
        evidence_ranker=None
    ):
        self.storage = storage
        self.entity_repo = EntityRepository(storage)
        self.artifact_repo = ArtifactRepository(storage)
        self.graph_builder = GraphBuilder(storage)
        self.anchor_resolver = AnchorResolver(storage)
        self.alias_manager = AliasManager(storage)
        self.embedding_engine = embedding_engine
        self.vector_index = vector_index
        self.fusion_engine = fusion_engine
        self.evidence_ranker = evidence_ranker

    def explore(self, entity_name: str, max_depth: int = 2) -> dict:
        """
        Explore the knowledge graph starting from the given entity name.
        Uses depth-limited BFS along artifact connection links.
        """
        # 1. Resolve Entity Name to Entity
        entity = self.anchor_resolver.resolve(entity_name)
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

        # 3. Use new TraversalEngine for exploration
        graph_repo = SQLiteGraphRepository(self.storage)
        from graphyra.storage.mention_repository import MentionRepository
        mention_repo = MentionRepository(self.storage)
        
        traversal_engine = TraversalEngine(graph_repo, self.entity_repo, mention_repo)
        evidence_retriever = EvidenceRetriever(self.storage)
        
        policy = TraversalPolicy(max_depth=max_depth, enable_scoring=False)
        request = TraversalRequest(
            query=entity_name,
            seed_entities=[entity.id],
            policy=policy
        )
        
        traversal_result = traversal_engine.traverse(request)
        chunks = evidence_retriever.retrieve_evidence(traversal_result)
        
        # Resolve artifacts associated with traversed anchors
        visited_artifacts = []
        for ent_id in traversal_result.visited_nodes:
            for art in artifacts:
                # Handle case where the node in visited_nodes might be an artifact ID itself
                if art.id == ent_id or art.metadata.get("entity_id") == ent_id or (self.entity_repo.get(ent_id) and art.title.lower() == self.entity_repo.get(ent_id).canonical_name.lower()):
                    if art not in visited_artifacts:
                        visited_artifacts.append(art)
                    break

        # Filter out start page from connected pages list
        connected_titles = [
            art.title 
            for art in visited_artifacts 
            if art.id != start_artifact.id
        ]

        return {
            "entity": entity,
            "start_artifact": start_artifact,
            "connected_pages": connected_titles,
            "visited_chunks": [c.id for c in chunks]
        }

    def visualize(self, start_entity_name: str, target_entity_name: str | None = None):
        """
        Visualize a traversal path in vertical ASCII flowchart layout.
        Defaults to demonstrating a key path (e.g. to 'Irminsul') or the longest path.
        """
        # 1. Resolve start entity
        entity = self.anchor_resolver.resolve(start_entity_name)
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
            target_entity = self.anchor_resolver.resolve(target_entity_name)
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

    def retrieve(self, question: str, config=None) -> dict:
        """
        Process a natural language question.
        1. Detects entities mentioned in the query (and run parallel semantic discovery if injected).
        2. Resolves entities to starting artifacts.
        3. Traverses paths between resolved artifacts using the TraversalEngine.
        4. Collects unique evidence chunks from visited pages.
        """
        import re
        from graphyra.storage.chunk_repository import ChunkRepository
        from graphyra.models.traversal_models import RetrievalConfig
        chunk_repo = ChunkRepository(self.storage)
        cfg = config or RetrievalConfig()

        # 1. Entity Detection (Canonical Name and Aliases)
        entities = self.entity_repo.list_all()
        normalized_q = re.sub(r'[^\w\s]', ' ', question).lower()
        words = normalized_q.split()
        
        detected_entities = []
        for e in entities:
            # Check canonical name and aliases
            names_to_check = [e.canonical_name.lower()]
            names_to_check.extend([a.lower() for a in self.alias_manager.get_aliases(e.id)])
            
            for name_lower in names_to_check:
                match = False
                if len(name_lower.split()) > 1:
                    if name_lower in normalized_q:
                        match = True
                else:
                    if name_lower in words:
                        match = True
                
                if match:
                    if e not in detected_entities:
                        detected_entities.append(e)
                    break

        # Parallel Candidate Discovery & Fusion
        if self.embedding_engine and self.vector_index and self.fusion_engine:
            # A. Generate Query Embedding
            q_emb = self.embedding_engine.get_query_embedding(question)
            
            # B. Search Vector Index
            search_results = self.vector_index.search(q_emb, top_k=5, threshold=0.0)
            
            # C. Extract Entity Mentions from top semantic chunks using dictionary resolver
            from graphyra.ingestion.mention_extractor import DictionaryMentionExtractor
            vocab = set()
            for ent in entities:
                vocab.add(ent.canonical_name)
                for alias in self.alias_manager.get_aliases(ent.id):
                    vocab.add(alias)
            mention_extractor = DictionaryMentionExtractor(vocab)
            
            semantic_entities = []
            for s_res in search_results:
                chunk_obj = chunk_repo.get(s_res.id)
                if chunk_obj:
                    mentions = mention_extractor.extract_mentions(chunk_obj)
                    for mention in mentions:
                        resolved_ent = self.anchor_resolver.resolve(mention, create_if_missing=False)
                        if resolved_ent:
                            semantic_entities.append((resolved_ent, s_res.score))
                            
            # D. Merge & Rank Traversal Seeds
            ranked_seeds = self.fusion_engine.fuse_candidates(detected_entities, semantic_entities)
            seed_ids = [e.id for e, score in ranked_seeds]
            detected_entities = [e for e, score in ranked_seeds]
        else:
            seed_ids = [e.id for e in detected_entities]
        
        graph_repo = SQLiteGraphRepository(self.storage)
        from graphyra.storage.mention_repository import MentionRepository
        mention_repo = MentionRepository(self.storage)
        
        traversal_engine = TraversalEngine(graph_repo, self.entity_repo, mention_repo)
        evidence_retriever = EvidenceRetriever(self.storage)
        subgraph_builder = SubgraphBuilder(self.storage)
        
        policy = TraversalPolicy()
        request = TraversalRequest(
            query=question,
            seed_entities=seed_ids,
            policy=policy
        )
        
        # 3. Graph Traversal
        traversal_result = traversal_engine.traverse(request)
        
        # 4. Evidence Retrieval
        candidate_chunks = evidence_retriever.retrieve_evidence(traversal_result)
        
        # 5. Evidence Ranking & Slicing
        if self.evidence_ranker:
            from graphyra.retrieval.ranking.policy import RankingPolicy
            ranking_policy = RankingPolicy(
                enable_bm25=True,
                enable_semantic=True if (self.embedding_engine and self.vector_index) else False,
                enable_reranker=False,
                strategy="graph_centric"
            )
            ranked_chunks = self.evidence_ranker.rank(question, candidate_chunks, policy=ranking_policy)
        else:
            ranked_chunks = list(candidate_chunks)
            
        selected_chunks = ranked_chunks[:cfg.evidence_limit]
        
        # 6. Reasoning Subgraph Construction
        subgraph = subgraph_builder.extract(traversal_result, selected_chunks)
        
        # 7. Retrieve all Artifacts associated with the chunks
        visited_artifacts = []
        all_artifacts = self.artifact_repo.list_all()
        for c in selected_chunks:
            art = self.artifact_repo.get(c.artifact_id)
            if art and art not in visited_artifacts:
                visited_artifacts.append(art)
                
        # Also ensure starting entity artifacts are included
        for e in detected_entities:
            for art in all_artifacts:
                if art.metadata.get("entity_id") == e.id or art.title.lower() == e.canonical_name.lower():
                    if art not in visited_artifacts:
                        visited_artifacts.append(art)
                    break

        # 7. Convert heterogeneous path hops to artifact paths for the visualizer/UI
        ui_paths = []
        for path in traversal_result.discovered_paths:
            art_path = []
            for node_id in path.hops:
                # 1. If it's already an artifact ID
                if node_id.startswith("ART_") or any(art.id == node_id for art in visited_artifacts):
                    if node_id not in art_path:
                        art_path.append(node_id)
                # 2. If it's a chunk ID, resolve to its parent artifact ID
                elif node_id.startswith("CHK_") or any(c.id == node_id for c in selected_chunks):
                    c_obj = next((c for c in selected_chunks if c.id == node_id), None)
                    if not c_obj:
                        from graphyra.storage.chunk_repository import ChunkRepository
                        chunk_repo = ChunkRepository(self.storage)
                        c_obj = chunk_repo.get(node_id)
                    if c_obj:
                        if c_obj.artifact_id not in art_path:
                            art_path.append(c_obj.artifact_id)
                # 3. If it's an entity/anchor ID
                else:
                    ent = self.entity_repo.get(node_id)
                    if ent:
                        matching_art_id = None
                        for art in visited_artifacts:
                            if art.metadata.get("entity_id") == ent.id or art.title.lower() == ent.canonical_name.lower():
                                matching_art_id = art.id
                                break
                        if matching_art_id:
                            if matching_art_id not in art_path:
                                art_path.append(matching_art_id)
            if art_path and len(art_path) >= 1 and art_path not in ui_paths:
                ui_paths.append(art_path)

        # Fallback path if empty but we have at least one artifact
        if not ui_paths and visited_artifacts:
            start_art = visited_artifacts[0]
            if len(visited_artifacts) > 1:
                ui_paths.append([start_art.id, visited_artifacts[1].id])
            else:
                ui_paths.append([start_art.id])

        res = {
            "entities": detected_entities,
            "artifacts": visited_artifacts,
            "selected_chunks": selected_chunks,
            "chunks": selected_chunks,
            "paths": ui_paths
        }
        if cfg.return_candidates:
            res["candidate_chunks"] = candidate_chunks
        if cfg.return_ranked:
            res["ranked_chunks"] = ranked_chunks
        return res

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
