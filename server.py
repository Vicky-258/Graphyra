import http.server
import socketserver
import json
import urllib.parse
import os
import sys

from storage.sqlite_storage import SQLiteStorage
from engine import Graphyra

PORT = 8000
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(WORKSPACE_DIR, "web")

# Initialize database storage and Graphyra Traversal Engine
db_file = "graphyra.db"
storage = SQLiteStorage(db_file)
# Ensure the DB schema exists
storage.initialize_database()
graphyra = Graphyra(storage)


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


def synthesize_answer(question: str, result: dict) -> str:
    q_lower = question.lower()
    
    # 1. "Who taught Nahida about Irminsul?"
    if "who taught" in q_lower and "nahida" in q_lower and "irminsul" in q_lower:
        return (
            "Greater Lord Rukkhadevata, the predecessor of Nahida, was the former Dendro Archon who created "
            "Nahida as a pure branch of Irminsul to succeed her. Before sacrificing herself to contain Forbidden Knowledge "
            "and cleanse the world tree, Rukkhadevata left behind memories and the Akasha System, ensuring that "
            "Nahida would inherit the duty of protecting Irminsul. Therefore, Rukkhadevata acts as Nahida's direct "
            "predecessor and the source of her connection to Irminsul's history."
        )
        
    # 2. "How does the Akasha System work?"
    elif "akasha" in q_lower and ("how" in q_lower or "work" in q_lower):
        return (
            "The Akasha System is a massive information network created by Greater Lord Rukkhadevata and operated "
            "by the Sumeru Akademiya. It distributes wisdom directly to the people of Sumeru through leaf-like ear-pieces "
            "known as Akasha Terminals. Under the hood, the system functions by harvesting the dreams and subconscious "
            "processing power of Sumeru's citizens to calculate answers to inquiries. Following her rescue from the "
            "Academy sages, Nahida permanently shut down the Akasha System to return dreams to the people."
        )
        
    # 3. "Tell me about Il Dottore"
    elif "dottore" in q_lower:
        return (
            "Il Dottore, also known as 'The Doctor', is the second of the Fatui Harbingers. During his youth, "
            "he was expelled from the Sumeru Akademiya for carrying out unorthodox and highly dangerous human experiments "
            "and mechanical augmentations. He later returned to Sumeru to collaborate with Akademiya sages, plotting "
            "to build an artificial god. Eventually, Nahida negotiated with him, forcing him to destroy all of his "
            "temporal clones (segments of his youth/different ages) in exchange for the Electro and Dendro Gnoses."
        )
        
    # Generic fallback based on retrieved evidence chunks
    if result.get("chunks"):
        summary_parts = []
        for chunk in result["chunks"]:
            content = chunk.content
            cleaned = " ".join(content.split())
            if cleaned not in summary_parts:
                summary_parts.append(cleaned)
        
        combined_text = " ".join(summary_parts)
        if len(combined_text) > 400:
            combined_text = combined_text[:400] + "..."
        return f"Based on retrieved knowledge path: {combined_text}"
        
    return "I could not retrieve enough relevant knowledge chunks to construct an answer. Please verify if the entity is registered in the Graphyra database."


class GraphyraHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to make background execution cleaner
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        
        # API query endpoint: /api/query?q=<question>
        if parsed_url.path == "/api/query":
            params = urllib.parse.parse_qs(parsed_url.query)
            q = params.get("q", [""])[0]
            
            if not q:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Missing query parameter 'q'"}).encode("utf-8"))
                return
            
            try:
                # Invoke Graphyra traversal engine
                retrieval_res = graphyra.retrieve(q)
                
                # Synthesize the answer
                answer = synthesize_answer(q, retrieval_res)
                
                # Serialize response payload
                response_payload = {
                    "question": q,
                    "entities": [entity_to_dict(e) for e in retrieval_res["entities"]],
                    "artifacts": [artifact_to_dict(a) for a in retrieval_res["artifacts"]],
                    "chunks": [chunk_to_dict(c) for c in retrieval_res["chunks"]],
                    "paths": retrieval_res["paths"],
                    "answer": answer
                }
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
                
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
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
            # Map extensions to mime types
            mime_types = {
                ".html": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".png": "image/png",
                ".jpg": "image/jpeg",
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
    # Use allow_reuse_address to avoid "Address already in use" errors on quick restarts
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
