# Storage Subsystem & Database Schemas

Graphyra employs a relational-graph storage topology inside [storage/sqlite_storage.py](file:///home/vicky/v_drive/Codes/Graphyra/storage/sqlite_storage.py), using SQLite tables to store knowledge assets, connections, and metadata.

---

## 1. Relational Database Schema (`graphyra.db`)

The database contains the following structural tables:

### 1.1 `artifacts` (Pages / Source Documents)
Stores the parent source files, titles, and crawler details.
* `id` (TEXT PRIMARY KEY): Unique identifier (e.g. `ART_001`).
* `title` (TEXT NOT NULL): Title of the page (e.g., `"Nahida"`).
* `source_type` (TEXT NOT NULL): Source origin type (e.g., `"wiki"`, `"pdf"`).
* `source` (TEXT): File path or source URL.
* `metadata` (TEXT): JSON string storing custom page metrics.

### 1.2 `chunks` (Text Segments)
Stores segmented text paragraphs referencing their parent page.
* `id` (TEXT PRIMARY KEY): Unique identifier (e.g. `CHK_001`).
* `artifact_id` (TEXT NOT NULL): Foreign key referencing `artifacts(id)` on delete cascade.
* `content` (TEXT NOT NULL): Segmented raw paragraph text.
* `embedding` (TEXT): [Optional] Cached vector array representation (historical).
* `metadata` (TEXT): JSON string storing line boundaries and tags.

### 1.3 `entities` (Retrieval Anchors)
Stores canonical names and concepts extracted as graph nodes.
* `id` (TEXT PRIMARY KEY): Unique identifier (e.g. `ENT_001`).
* `canonical_name` (TEXT NOT NULL): Canonical anchor term (e.g. `"Irminsul"`).
* `entity_type` (TEXT NOT NULL): Entity category (e.g. `"PERSON"`, `"LOCATION"`, `"EVENT"`).
* `metadata` (TEXT): JSON string.

### 1.4 `aliases` (Redirect Terms)
Maps search queries and synonym redirects to canonical entities.
* `entity_id` (TEXT NOT NULL): Foreign key referencing `entities(id)` on delete cascade.
* `alias` (TEXT NOT NULL): Synonym or alternative name (e.g. `"Lesser Lord Kusanali"`).

### 1.5 `entity_mentions` (Provenance Indices)
Intersection table mapping which chunks contain occurrences of entities.
* `entity_id` (TEXT NOT NULL): Foreign key referencing `entities(id)`.
* `chunk_id` (TEXT NOT NULL): Foreign key referencing `chunks(id)`.

### 1.6 `relations` (Graph Edges)
Stores semantic connections between entities.
* `id` (TEXT PRIMARY KEY): Unique identifier.
* `source_id` (TEXT NOT NULL): Origin entity ID.
* `target_id` (TEXT NOT NULL): Target entity ID.
* `relation_type` (TEXT NOT NULL): Relationship description (e.g., `"ruler_of"`, `"member_of"`).
* `metadata` (TEXT): JSON string storing relation weights.

### 1.7 `artifact_links` (Structural Connections)
Stores hyperlink navigations between page documents.
* `source_artifact_id` (TEXT NOT NULL): Origin page ID.
* `target_artifact_id` (TEXT NOT NULL): Target page ID.

---

## 2. Thread-Local Connections & Proxies

To prevent threading access collisions across background sync jobs and async server requests:
* **`SQLiteConnectionProxy`**: Wraps the raw sqlite3 connection. Defers commits when running inside a bulk crawler sync transaction (`bulk_transaction()`), reducing write I/O overhead.
* **Thread-Local Storage**: `SQLiteStorage` caches the connection proxy inside `threading.local()`, ensuring each OS thread owns a private database handler.

---

## 3. Decoupled Repository Pattern

All SQL statements are isolated from the query execution engines using repositories:
* **`GraphRepository`**: Exposes the abstract graph interface. The concrete implementation [SQLiteGraphRepository](file:///home/vicky/v_drive/Codes/Graphyra/storage/graph_repository.py) runs query lookups to retrieve neighbor nodes (`get_neighbors(entity_id)`). This allows the traversal engine to remain completely database-agnostic.
* **Entity / Chunk Repositories**: Read and write entity records, chunk properties, and references through standard objects (`Entity`, `Chunk`, `Artifact`).
