# Graphyra: Graph-Constrained Retrieval (GCR) Engine

Graphyra is a Proof of Concept (POC) demonstrating **Graph-Constrained Retrieval (GCR)**. Traditional RAG retrieval treats text chunks as isolated vectors, which fails for complex, multi-hop queries. Graphyra solves this by retaining document chunks but layering a reference navigation graph on top, walking relations from document to document to extract exact evidence.

---

## Key Features

1. **Entity Extraction & Resolution**: Scans user questions to detect key concepts (People, Locations, Concepts) and resolves them to their corresponding documentation folders.
2. **Graph Traversal (BFS & Shortest Path)**: Uses NetworkX to trace reference links connecting documents. It can walk paths from start pages to target pages (e.g. `Nahida` $\rightarrow$ `Greater Lord Rukkhadevata` $\rightarrow$ `Irminsul`).
3. **Evidence Extraction**: Compiles exact paragraph chunks along the traversal path to gather context.
4. **Interactive Storytelling UI**: A premium matte dark timeline interface that visualizes the retrieval steps in conversational English, showing anyone *how* the engine got the answer.

---

## Folder Structure

```text
Graphyra/
├── data/
│   └── sumeru_demo_corpus.json      # 10 connected page wiki data (Sumeru lore)
├── models/                          # Database dataclasses (Entities, Artifacts, Chunks)
├── storage/                         # Repositories executing SQLite queries
├── utils/
│   ├── graph_builder.py             # Compiles NetworkX graph from SQLite tables
│   └── seed_db.py                   # Re-seeds database with local corpus
├── web/
│   ├── index.html                   # Storyboard UI markup
│   ├── style.css                    # Matte dark theme style system
│   └── app.js                       # Frontend visual timeline rendering
├── engine.py                        # GCR search, traversal pathing, and ASCII traces
├── main.py                          # CLI runner for quick reasoning traces
└── server.py                        # Zero-dependency Python HTTP API server
```

---

## Getting Started

### 1. Database Seeding & CLI Trace
To initialize the SQLite database (`graphyra.db`), seed the Sumeru wiki corpus, and verify a CLI trace, run:
```bash
python main.py
```

This will seed the database and output an ASCII reasoning trace for the question: *"Who taught Nahida about Irminsul?"*
```text
--- Running Reasoning Trace for: "Who taught Nahida about Irminsul?" ---
Detected Entity:
Nahida
Irminsul

Resolved Artifact:
Nahida Page
Irminsul Page

Traversal:
Nahida Page
↓
Rukkhadevata Page
↓
Irminsul Page
```

### 2. Running the Storyboard Web UI
To spin up the local server and try searches in the web browser, launch the zero-dependency Python server:
```bash
python server.py
```

Then open your browser and navigate to:
```text
http://localhost:8000
```

Try clicking the suggestions on the screen (such as *"Who taught Nahida about Irminsul?"* or *"How does the Akasha System work?"*) to witness the step-by-step timeline explanation.

---

## Technical Details & Shortcuts

* **Database**: Persisted locally in SQLite. The database maps entity mentions inside chunks, as well as citation links between parent documents.
* **Graphing**: Recompiled into a NetworkX DiGraph on demand in the engine.
* **Answer Synthesis (Sandbox Limitation)**: Because the system is designed to run in a sandboxed, zero-dependency offline environment, the final text generation step is handled by a rule-based parser mapping primary query subjects, falling back to chunk summaries for other topics.
* **Detailed Audit**: For a full list of hardcoded logic, corners cut, and production next steps, see the internal documentation file at `brain/383ec70c-b76d-42a8-9410-bda4029ae1eb/system_architecture_and_debts.md`.
