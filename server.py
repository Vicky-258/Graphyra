import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import time
import traceback
import signal

def dump_stack(sig, frame):
    print("--- Stack Trace Dump ---", flush=True)
    for thread_id, stack in sys._current_frames().items():
        print(f"\nThread {thread_id}:", flush=True)
        traceback.print_stack(stack)
    print("------------------------", flush=True)

signal.signal(signal.SIGUSR1, dump_stack)

from storage.sqlite_storage import SQLiteStorage
from storage.entity_repository import EntityRepository
from storage.artifact_repository import ArtifactRepository
from storage.relation_repository import RelationRepository
from storage.chunk_repository import ChunkRepository
from storage.mention_repository import MentionRepository
from storage.anchor_resolver import AnchorResolver
from models.traversal_models import TraversalRequest, TraversalPolicy
from traversal_engine import TraversalEngine
from storage.graph_repository import SQLiteGraphRepository
from storage.evidence_retriever import EvidenceRetriever
from subgraph_builder import SubgraphBuilder
from utils.jobs import JobManager, JobRegistry
from engine import Graphyra

PORT = 8000
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(WORKSPACE_DIR, "web")

db_file = "graphyra.db"
storage = SQLiteStorage(db_file)
storage.initialize_database()

# Bootstrap and inject Semantic Retrieval Layer
from semantic.bootstrap import bootstrap_semantic_layer
emb_engine, vec_index, fus_engine, indexer = bootstrap_semantic_layer(storage, db_path="embeddings.db")
graphyra = Graphyra(
    storage=storage,
    embedding_engine=emb_engine,
    vector_index=vec_index,
    fusion_engine=fus_engine
)

entity_repo = EntityRepository(storage)
artifact_repo = ArtifactRepository(storage)
relation_repo = RelationRepository(storage)
chunk_repo = ChunkRepository(storage)
mention_repo = MentionRepository(storage)
anchor_resolver = AnchorResolver(storage)


def entity_to_dict(e):
    return {
        "id": e.id,
        "canonical_name": e.canonical_name,
        "entity_type": e.entity_type.value,
        "metadata": e.metadata
    }


def artifact_to_dict(a):
    return {
        "id": a.id,
        "title": a.title,
        "source_type": a.source_type,
        "source": a.source,
        "metadata": a.metadata
    }


def chunk_to_dict(c):
    return {
        "id": c.id,
        "artifact_id": c.artifact_id,
        "content": c.content,
        "metadata": c.metadata
    }


class GraphyraHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Override to suppress verbose HTTP console logging
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""

        # CORS Support for API Dev Server
        def send_json_response(status_code, payload):
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        try:
            # 1. Reset Database endpoint
            if parsed_url.path == "/api/reset":
                with storage.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM relations")
                    cursor.execute("DELETE FROM chunks")
                    cursor.execute("DELETE FROM artifacts")
                    cursor.execute("DELETE FROM entity_mentions")
                    cursor.execute("DELETE FROM aliases")
                    cursor.execute("DELETE FROM entities")
                    cursor.execute("DELETE FROM artifact_links")
                    cursor.execute("DELETE FROM evidence_references")
                    conn.commit()
                if hasattr(storage, "clear_id_cache"):
                    storage.clear_id_cache()
                send_json_response(200, {"status": "ok", "message": "Database cleared successfully."})
                return

            # 2. Trigger asynchronous background crawl
            elif parsed_url.path == "/api/crawl":
                job_id = JobManager.submit_crawl_job(storage)
                send_json_response(200, {"job_id": job_id, "status": "running"})
                return

            # 3. Traversal Query engine execution
            elif parsed_url.path == "/api/query":
                payload = json.loads(post_data.decode("utf-8")) if post_data else {}
                q = payload.get("q", "").strip()
                max_depth = int(payload.get("max_depth", 2))
                enable_scoring = bool(payload.get("enable_scoring", True))

                if not q:
                    send_json_response(400, {"error": "Missing parameter 'q'"})
                    return

                # Record query execution diagnostics
                start_time = time.time()

                # Step 1: Resolve Entry Point Anchors
                # Entity detection
                entities = entity_repo.list_all()
                import re
                normalized_q = re.sub(r'[^\w\s]', ' ', q).lower()
                words = normalized_q.split()
                
                detected = []
                for e in entities:
                    names_to_check = [e.canonical_name.lower()]
                    names_to_check.extend([a.lower() for a in self.headers.get("aliases", "").split(",")]) # or check local manager
                    
                    # Fetch real aliases from AliasManager
                    from storage.alias_manager import AliasManager
                    alias_mgr = AliasManager(storage)
                    names_to_check.extend([a.lower() for a in alias_mgr.get_aliases(e.id)])

                    for name_lower in names_to_check:
                        match = False
                        if len(name_lower.split()) > 1:
                            if name_lower in normalized_q:
                                match = True
                        else:
                            if name_lower in words:
                                match = True
                        if match:
                            if e not in detected:
                                detected.append(e)
                            break

                seed_ids = [e.id for e in detected]

                # Step 2: Execute Traversal
                graph_repo = SQLiteGraphRepository(storage)
                traversal_engine = TraversalEngine(graph_repo, entity_repo, mention_repo)
                evidence_retriever = EvidenceRetriever(storage)
                subgraph_builder = SubgraphBuilder(storage)

                policy = TraversalPolicy(max_depth=max_depth, enable_scoring=enable_scoring)
                request = TraversalRequest(query=q, seed_entities=seed_ids, policy=policy)

                traversal_res = traversal_engine.traverse(request)
                chunks = evidence_retriever.retrieve_evidence(traversal_res)
                subgraph = subgraph_builder.extract(traversal_res, chunks)

                # Resolve artifact records
                all_artifacts = artifact_repo.list_all()
                visited_artifacts = []
                for c in chunks:
                    art = artifact_repo.get(c.artifact_id)
                    if art and art not in visited_artifacts:
                        visited_artifacts.append(art)
                for e in detected:
                    for art in all_artifacts:
                        if art.metadata.get("entity_id") == e.id or art.title.lower() == e.canonical_name.lower():
                            if art not in visited_artifacts:
                                visited_artifacts.append(art)
                            break

                # Create text trace route
                trace_steps = []
                trace_steps.append(f"Query parsed: '{q}'")
                if detected:
                    trace_steps.append(f"Detected seed anchors: {', '.join([e.canonical_name for e in detected])}")
                else:
                    trace_steps.append("No seed anchors detected directly in query. Starting traversal from all known anchors.")
                
                trace_steps.append(f"Traversing graph repository (max_depth={max_depth}, scoring={enable_scoring})")
                trace_steps.append(f"Visited {len(traversal_res.visited_nodes)} nodes: {', '.join(traversal_res.visited_nodes)}")
                trace_steps.append(f"Discovered {len(traversal_res.discovered_paths)} traversal paths.")
                trace_steps.append(f"Retrieved {len(chunks)} evidence sentences.")

                latency_ms = round((time.time() - start_time) * 1000, 2)

                # Render subgraph response data
                response_payload = {
                    "question": q,
                    "seed_anchors": [entity_to_dict(e) for e in detected],
                    "visited_nodes": traversal_res.visited_nodes,
                    "discovered_paths": [
                        {
                            "seed_entity": p.seed_entity,
                            "target_entity": p.target_entity,
                            "hops": p.hops,
                            "relations": p.relations,
                            "depth": p.depth,
                            "score": round(p.score, 3)
                        } for p in traversal_res.discovered_paths
                    ],
                    "evidence_chunks": [
                        {
                            "id": c.id,
                            "artifact_id": c.artifact_id,
                            "artifact_title": next((a.title for a in visited_artifacts if a.id == c.artifact_id), "Unknown"),
                            "content": c.content,
                            "score": round(traversal_res.scores.get(c.id, 0.0), 3) if enable_scoring else 1.0
                        } for c in chunks
                    ],
                    "subgraph": {
                        "entities": subgraph.entities,
                        "relations": [
                            {
                                "source": r.source,
                                "target": r.target,
                                "relation_type": r.relation_type,
                                "score": round(r.score, 3)
                            } for r in subgraph.relations
                        ],
                        "chunks": [c.id for c in subgraph.chunks],
                        "paths": [
                            {
                                "hops": p.hops,
                                "relations": p.relations,
                                "score": round(p.score, 3)
                            } for p in subgraph.paths
                        ]
                    },
                    "trace_steps": trace_steps,
                    "diagnostics": {
                        "latency_ms": latency_ms,
                        "nodes_expanded": len(traversal_res.visited_nodes),
                        "paths_discovered": len(traversal_res.discovered_paths),
                        "budget_limit": policy.max_depth
                    }
                }
                send_json_response(200, response_payload)
                return

            else:
                send_json_response(404, {"error": "Endpoint not found"})
                return

        except Exception as err:
            send_json_response(500, {"error": str(err), "traceback": traceback.format_exc()})

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)

        def send_json_response(status_code, payload):
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        # CORS preflight fallback inside GET
        if parsed_url.path == "/api/stats":
            try:
                with storage.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Basic counts
                    cursor.execute("SELECT COUNT(*) FROM artifacts")
                    artifacts_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM chunks")
                    chunks_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM entities")
                    anchors_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM relations")
                    relations_count = cursor.fetchone()[0]

                    # Auto-registered anchors count
                    cursor.execute("SELECT COUNT(*) FROM entities WHERE metadata LIKE '%auto_created%'")
                    auto_registered_anchors = cursor.fetchone()[0]

                    # Mention count & density
                    cursor.execute("SELECT COUNT(*) FROM entity_mentions")
                    total_mentions = cursor.fetchone()[0]
                    mention_density = total_mentions / chunks_count if chunks_count > 0 else 0.0

                    # Redirect aliases count
                    cursor.execute("SELECT COUNT(*) FROM relations WHERE relation_type = 'redirects_to'")
                    redirect_aliases_count = cursor.fetchone()[0]

                    # Relations breakdown
                    cursor.execute("SELECT relation_type, COUNT(*) FROM relations GROUP BY relation_type")
                    relation_breakdown = {row[0]: row[1] for row in cursor.fetchall()}

                    # Duplicate chunks count & lists
                    cursor.execute("""
                        SELECT content, COUNT(*) as group_count
                        FROM chunks
                        GROUP BY content
                        HAVING group_count > 1
                        ORDER BY group_count DESC
                    """)
                    dup_rows = cursor.fetchall()
                    duplicate_chunks_count = len(dup_rows)
                    top_duplicate_chunks = [{"content": r[0], "count": r[1]} for r in dup_rows[:5]]

                    # Coverage metrics
                    cursor.execute("""
                        SELECT id, title FROM artifacts
                        WHERE LOWER(title) NOT IN (SELECT LOWER(canonical_name) FROM entities)
                          AND LOWER(title) NOT IN (SELECT LOWER(alias) FROM aliases)
                    """)
                    missing_art_rows = cursor.fetchall()
                    missing_artifacts_count = len(missing_art_rows)
                    top_missing_artifacts = [{"id": r[0], "title": r[1]} for r in missing_art_rows[:5]]
                    anchor_coverage_pct = ((artifacts_count - missing_artifacts_count) / artifacts_count * 100) if artifacts_count > 0 else 0.0

                    # Chunk lengths and word sizes
                    cursor.execute("SELECT content FROM chunks")
                    chunk_contents = [row[0] for row in cursor.fetchall()]
                    
                    if chunk_contents:
                        lengths_char = [len(c) for c in chunk_contents]
                        word_counts = [len(c.split()) for c in chunk_contents]
                        
                        avg_chunk_len = sum(lengths_char) / len(lengths_char)
                        sorted_lengths = sorted(lengths_char)
                        median_chunk_len = sorted_lengths[len(sorted_lengths)//2]
                        shortest_chunk = min(lengths_char)
                        longest_chunk = max(lengths_char)
                        
                        chunks_less_100_words = sum(1 for w in word_counts if w < 100)
                        chunks_greater_max_size = sum(1 for w in word_counts if w > 400)
                        
                        # Build word count histogram in buckets of 50
                        histogram = {}
                        for wc in word_counts:
                            bucket = (wc // 50) * 50
                            bucket_str = f"{bucket}-{bucket+49}"
                            histogram[bucket_str] = histogram.get(bucket_str, 0) + 1
                    else:
                        avg_chunk_len = 0.0
                        median_chunk_len = 0
                        shortest_chunk = 0
                        longest_chunk = 0
                        chunks_less_100_words = 0
                        chunks_greater_max_size = 0
                        histogram = {}

                    # Actionable Debug Lists
                    # Shortest chunks
                    cursor.execute("SELECT id, artifact_id, LENGTH(content) as len, content FROM chunks ORDER BY len ASC LIMIT 5")
                    top_shortest_chunks = [{"id": r[0], "artifact_id": r[1], "length": r[2], "content": r[3]} for r in cursor.fetchall()]

                    # Longest chunks
                    cursor.execute("SELECT id, artifact_id, LENGTH(content) as len, content FROM chunks ORDER BY len DESC LIMIT 5")
                    top_longest_chunks = [{"id": r[0], "artifact_id": r[1], "length": r[2], "content": r[3]} for r in cursor.fetchall()]

                    # Chunks without mentions
                    cursor.execute("""
                        SELECT id, artifact_id, content FROM chunks
                        WHERE id NOT IN (SELECT DISTINCT chunk_id FROM entity_mentions)
                        LIMIT 5
                    """)
                    top_chunks_no_mentions = [{"id": r[0], "artifact_id": r[1], "content": r[2]} for r in cursor.fetchall()]
                    cursor.execute("SELECT COUNT(*) FROM chunks WHERE id NOT IN (SELECT DISTINCT chunk_id FROM entity_mentions)")
                    chunks_no_mentions_count = cursor.fetchone()[0]

                    # Artifacts with highest chunk counts
                    cursor.execute("""
                        SELECT c.artifact_id, a.title, COUNT(*) as c_count
                        FROM chunks c
                        JOIN artifacts a ON c.artifact_id = a.id
                        GROUP BY c.artifact_id
                        ORDER BY c_count DESC
                        LIMIT 5
                    """)
                    top_artifacts_highest_chunks = [{"id": r[0], "title": r[1], "chunk_count": r[2]} for r in cursor.fetchall()]

                payload = {
                    "db_size_bytes": os.path.getsize(db_file) if os.path.exists(db_file) else 0,
                    "fts_health": "Healthy",
                    
                    "artifacts_count": artifacts_count,
                    "chunks_count": chunks_count,
                    "anchors_count": anchors_count,
                    "relations_count": relations_count,
                    
                    "auto_registered_anchors": auto_registered_anchors,
                    "mention_density": round(mention_density, 3),
                    "redirect_aliases_count": redirect_aliases_count,
                    "relation_breakdown": relation_breakdown,
                    "duplicate_chunks_count": duplicate_chunks_count,
                    
                    "anchor_coverage_pct": round(anchor_coverage_pct, 2),
                    "missing_artifacts_count": missing_artifacts_count,
                    
                    "avg_chunk_length": round(avg_chunk_len, 2),
                    "median_chunk_length": median_chunk_len,
                    "shortest_chunk": shortest_chunk,
                    "longest_chunk": longest_chunk,
                    "chunks_less_100_words": chunks_less_100_words,
                    "chunks_greater_max_size": chunks_greater_max_size,
                    "chunk_size_histogram": histogram,
                    
                    # Actionable Debug Lists
                    "top_shortest_chunks": top_shortest_chunks,
                    "top_longest_chunks": top_longest_chunks,
                    "top_chunks_no_mentions": top_chunks_no_mentions,
                    "chunks_no_mentions_count": chunks_no_mentions_count,
                    "top_artifacts_highest_chunks": top_artifacts_highest_chunks,
                    "top_missing_artifacts": top_missing_artifacts,
                    "top_duplicate_chunks": top_duplicate_chunks
                }
                send_json_response(200, payload)
            except Exception as e:
                send_json_response(500, {"error": str(e), "traceback": traceback.format_exc()})
            return

        elif parsed_url.path.startswith("/api/jobs/"):
            job_id = parsed_url.path.split("/")[-1]
            job = JobRegistry.get(job_id)
            if not job:
                send_json_response(404, {"error": f"Job {job_id} not found."})
                return
            send_json_response(200, {
                "id": job.id,
                "status": job.status,
                "progress": job.progress,
                "message": job.message,
                "metrics": job.metrics,
                "error": job.error,
                "created_at": job.created_at,
                "completed_at": job.completed_at
            })
            return

        elif parsed_url.path == "/api/artifacts":
            try:
                artifacts = artifact_repo.list_all()
                send_json_response(200, [artifact_to_dict(art) for art in artifacts])
            except Exception as e:
                send_json_response(500, {"error": str(e)})
            return

        elif parsed_url.path.startswith("/api/artifact/"):
            art_id = parsed_url.path[len("/api/artifact/"):]
            art_id = urllib.parse.unquote(art_id)
            try:
                art = artifact_repo.get(art_id)
                if not art:
                    send_json_response(404, {"error": f"Artifact {art_id} not found"})
                    return
                
                # Fetch associated chunks
                chunks = chunk_repo.get_by_artifact(art_id)
                
                # Fetch outgoing links
                outgoing_rels = relation_repo.get_relations(source_id=art_id)
                outgoing_links = [
                    {"target_id": r.target_id, "relation_type": r.relation_type, "metadata": r.metadata}
                    for r in outgoing_rels
                ]
                
                # Fetch incoming links
                with storage.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, source_id, relation_type, metadata 
                        FROM relations 
                        WHERE target_id = ?
                    """, (art_id,))
                    incoming_rows = cursor.fetchall()
                    incoming_links = [
                        {"source_id": row[1], "relation_type": row[2], "metadata": json.loads(row[3] or "{}")}
                        for row in incoming_rows
                    ]

                    # Fetch mentions
                    cursor.execute("""
                        SELECT DISTINCT e.id, e.canonical_name 
                        FROM entity_mentions m
                        JOIN chunks c ON m.chunk_id = c.id
                        JOIN entities e ON m.entity_id = e.id
                        WHERE c.artifact_id = ?
                    """, (art_id,))
                    mentions_rows = cursor.fetchall()
                    resolved_anchors = [{"id": r[0], "canonical_name": r[1]} for r in mentions_rows]

                payload = {
                    "artifact": artifact_to_dict(art),
                    "chunks": [chunk_to_dict(c) for c in chunks],
                    "outgoing_links": outgoing_links,
                    "incoming_links": incoming_links,
                    "resolved_anchors": resolved_anchors
                }
                send_json_response(200, payload)
            except Exception as e:
                send_json_response(500, {"error": str(e), "traceback": traceback.format_exc()})
            return

        elif parsed_url.path == "/api/graph":
            try:
                # Support limit parameter to prevent browser crashes on large graphs
                query_params = urllib.parse.parse_qs(parsed_url.query)
                limit = 100
                if "limit" in query_params:
                    try:
                        limit = int(query_params["limit"][0])
                    except ValueError:
                        pass

                nodes = []
                edges = []
                added_node_ids = set()

                # Get the top semantic relations (excluding contains to chunks)
                with storage.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # 1. Fetch top relations limit
                    cursor.execute("""
                        SELECT id, source_id, target_id, relation_type, metadata
                        FROM relations
                        WHERE relation_type != 'contains'
                        LIMIT ?
                    """, (limit,))
                    relations_rows = cursor.fetchall()
                    
                    # 2. Fetch top implicit mentions (limit to balance mentions and structural links)
                    cursor.execute("""
                        SELECT DISTINCT c.artifact_id, m.entity_id 
                        FROM entity_mentions m 
                        JOIN chunks c ON m.chunk_id = c.id
                        LIMIT ?
                    """, (limit,))
                    mentions_rows = cursor.fetchall()

                    # Resolve labels/types for involved nodes
                    involved_ids = set()
                    for r in relations_rows:
                        involved_ids.add(r[1])
                        involved_ids.add(r[2])
                    for m in mentions_rows:
                        involved_ids.add(m[0])
                        involved_ids.add(m[1])

                    if involved_ids:
                        # Fetch artifacts details
                        placeholders = ",".join("?" for _ in involved_ids)
                        cursor.execute(f"SELECT id, title FROM artifacts WHERE id IN ({placeholders})", list(involved_ids))
                        art_map = {row[0]: row[1] for row in cursor.fetchall()}

                        # Fetch entities details
                        cursor.execute(f"SELECT id, canonical_name FROM entities WHERE id IN ({placeholders})", list(involved_ids))
                        ent_map = {row[0]: row[1] for row in cursor.fetchall()}
                    else:
                        art_map = {}
                        ent_map = {}

                # Build nodes
                for node_id in involved_ids:
                    if node_id in art_map:
                        nodes.append({
                            "data": {
                                "id": node_id,
                                "label": art_map[node_id],
                                "type": "artifact"
                            }
                        })
                    elif node_id in ent_map:
                        nodes.append({
                            "data": {
                                "id": node_id,
                                "label": ent_map[node_id],
                                "type": "anchor"
                            }
                        })

                # Build edges
                for r_id, src, tgt, r_type, meta_json in relations_rows:
                    if src in involved_ids and tgt in involved_ids:
                        edges.append({
                            "data": {
                                "id": r_id,
                                "source": src,
                                "target": tgt,
                                "label": r_type,
                                "type": r_type
                            }
                        })

                for idx, (art_id, ent_id) in enumerate(mentions_rows):
                    if art_id in involved_ids and ent_id in involved_ids:
                        edges.append({
                            "data": {
                                "id": f"men_{idx}",
                                "source": art_id,
                                "target": ent_id,
                                "label": "mentions",
                                "type": "mentions"
                            }
                        })

                send_json_response(200, {"nodes": nodes, "edges": edges})
            except Exception as e:
                send_json_response(500, {"error": str(e), "traceback": traceback.format_exc()})
            return

        # Serve static assets from the web/ directory
        filepath = parsed_url.path.lstrip("/")
        if not filepath or filepath == "index.html":
            filepath = "index.html"

        full_path = os.path.join(WEB_DIR, filepath)

        # Safety check: prevent directory traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(WEB_DIR)):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        if os.path.exists(full_path) and not os.path.isdir(full_path):
            mime_types = {
                ".html": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".svg": "image/svg+xml",
                ".ico": "image/x-icon"
            }
            _, ext = os.path.splitext(full_path)
            content_type = mime_types.get(ext.lower(), "application/octet-stream")

            try:
                with open(full_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Internal Server Error: {e}".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File Not Found")


def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), GraphyraHTTPRequestHandler) as httpd:
        print(f"Graphyra local web server running at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()


if __name__ == "__main__":
    run()
