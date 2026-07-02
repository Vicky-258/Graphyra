import sys
import json
import urllib.request
import urllib.parse
import argparse

# ANSI escape codes for coloring
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def send_query(server_url: str, query: str, max_depth: int, enable_scoring: bool) -> dict:
    url = f"{server_url.rstrip('/')}/api/query"
    payload = {
        "q": query,
        "max_depth": max_depth,
        "enable_scoring": enable_scoring
    }
    data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "GraphyraCLI/1.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"{RED}{BOLD}Error:{RESET} Could not connect to Graphyra server at {server_url}.")
        print("Please make sure the server is running (e.g., execute `python server.py` in the background).")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}{BOLD}Error:{RESET} Failed to execute query: {e}")
        sys.exit(1)

def print_tree_trace(data: dict):
    print(f"\n{BOLD}{CYAN}🔍 QUERY DETAILS{RESET}")
    print(f"  {BOLD}Question:{RESET} {data.get('question')}")
    print(f"  {BOLD}Latency:{RESET} {data.get('diagnostics', {}).get('latency_ms')} ms")
    
    # 1. Print Seed Anchors
    seeds = data.get("seed_anchors", [])
    print(f"\n{BOLD}{CYAN}⚓ SEED ANCHORS DETECTED{RESET}")
    if seeds:
        for s in seeds:
            print(f"  ├── {GREEN}{s.get('canonical_name')}{RESET} ({s.get('id')}) [{s.get('entity_type')}]")
    else:
        print(f"  └── {YELLOW}No seed anchors matched in query. Starting traversal from all anchors.{RESET}")

    # 2. Print Discovered Paths
    paths = data.get("discovered_paths", [])
    print(f"\n{BOLD}{CYAN}🛣️ DISCOVERED TRAVERSAL PATHS{RESET}")
    if paths:
        # Sort paths by score descending
        sorted_paths = sorted(paths, key=lambda x: x.get("score", 0.0), reverse=True)
        for i, p in enumerate(sorted_paths):
            marker = "└──" if i == len(sorted_paths) - 1 else "├──"
            
            # Print formatted hop sequence
            hops = p.get("hops", [])
            relations = p.get("relations", [])
            
            path_str = f"{GREEN}{hops[0]}{RESET}"
            for idx in range(1, len(hops)):
                rel_type = relations[idx-1] if idx-1 < len(relations) else "link"
                path_str += f" ──[{BLUE}{rel_type}{RESET}]──> {GREEN}{hops[idx]}{RESET}"
            
            print(f"  {marker} {path_str} (Score: {YELLOW}{p.get('score')}{RESET}, Depth: {p.get('depth')})")
    else:
        print(f"  └── {YELLOW}No traversal paths found.{RESET}")

    # 3. Print Evidence Chunks
    evidence = data.get("evidence_chunks", [])
    print(f"\n{BOLD}{CYAN}📖 RETRIEVED EVIDENCE CHUNKS{RESET}")
    if evidence:
        # Sort evidence by score descending
        sorted_evidence = sorted(evidence, key=lambda x: x.get("score", 0.0), reverse=True)
        for i, c in enumerate(sorted_evidence):
            print(f"  {BOLD}{i+1}. [{YELLOW}Score: {c.get('score')}{RESET}] {CYAN}{c.get('artifact_title')}{RESET} ({c.get('id')})")
            # Format text wrap for readability
            content = c.get("content", "").strip()
            print(f"     \"{content}\"\n")
    else:
        print(f"  └── {YELLOW}No evidence chunks retrieved.{RESET}")

def main():
    parser = argparse.ArgumentParser(
        description="Graphyra Developer Console CLI Query Tool. Connects to the running local server to execute traversals."
    )
    parser.add_argument("query", type=str, help="The query text to run through the traversal engine.")
    parser.add_argument("--depth", type=int, default=2, help="Maximum path traversal depth (default: 2).")
    parser.add_argument("--no-score", action="store_true", help="Disable score-based ranking on traversals.")
    parser.add_argument("--server", type=str, default="http://localhost:8000", help="Graphyra server URL (default: http://localhost:8000).")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON response rather than formatted tree representation.")
    
    args = parser.parse_args()
    
    enable_scoring = not args.no_score
    response = send_query(args.server, args.query, args.depth, enable_scoring)
    
    if args.raw:
        print(json.dumps(response, indent=2))
    else:
        print_tree_trace(response)

if __name__ == "__main__":
    main()
