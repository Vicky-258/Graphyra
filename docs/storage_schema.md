# Database Schema Reference

Graphyra persists knowledge graphs, document chunks, synonym mappings, and evidence metrics inside a relational database (`graphyra.db`) managed by the `SQLiteStorage` wrapper.

---

## Database Schema Diagram

```text
  artifacts ◄───[1:N]─── chunks
      │                    │
    [N:M]                [N:M] (via entity_mentions)
      │                    │
      ▼                    ▼
  artifact_links        entities ◄───[1:N]─── aliases
                           │
                         [N:M] (via relations)
```

---

## 1. Table Specifications

### 1.1 Table: `artifacts`
Stores primary document properties.
- **Fields**:
  - `id` (TEXT PRIMARY KEY): Unique identifier.
  - `title` (TEXT NOT NULL): Title of the page or document.
  - `source_type` (TEXT NOT NULL): Classification descriptor (e.g. `"wiki"`, `"pdf"`, `"markdown"`).
  - `source` (TEXT): Original file path, URI, or URL.
  - `metadata` (TEXT): JSON-stringified key-value dictionary storing crawl times or source hashes.
- **Indices**:
  - `idx_artifacts_title` ON `artifacts(title)` (Case-insensitive lookup index).

### 1.2 Table: `chunks`
Stores segmented paragraph text.
- **Fields**:
  - `id` (TEXT PRIMARY KEY): Unique identifier.
  - `artifact_id` (TEXT NOT NULL): Parent artifact ID. FOREIGN KEY references `artifacts(id)` ON DELETE CASCADE.
  - `content` (TEXT NOT NULL): Chunk text content.
  - `embedding` (TEXT): [Deprecated] Historical column.
  - `metadata` (TEXT): JSON-stringified dictionary storing token sizes or section bounds.
- **Indices**:
  - `idx_chunks_artifact` ON `chunks(artifact_id)` (Foreign key traversal optimization index).

### 1.3 Table: `entities`
Stores the knowledge graph canonical nodes.
- **Fields**:
  - `id` (TEXT PRIMARY KEY): Unique identifier.
  - `canonical_name` (TEXT NOT NULL): Primary canonical term index name.
  - `entity_type` (TEXT NOT NULL): Category enum tag (e.g. `"PERSON"`, `"LOCATION"`, `"CONCEPT"`).
  - `metadata` (TEXT): JSON-stringified dictionary.
- **Indices**:
  - `idx_entities_name` ON `entities(canonical_name)` (Unique/Case-insensitive search index).

### 1.4 Table: `aliases`
Stores query redirects and synonyms.
- **Fields**:
  - `entity_id` (TEXT NOT NULL): Target canonical entity ID. FOREIGN KEY references `entities(id)` ON DELETE CASCADE.
  - `alias` (TEXT NOT NULL): Alternative synonym term text.
- **Indices**:
  - `idx_aliases_alias` ON `aliases(alias)` (Alias resolving search index).
  - `idx_aliases_entity` ON `aliases(entity_id)` (Reverse lookup mapping index).

### 1.5 Table: `entity_mentions`
Maps entity occurrences inside chunks.
- **Fields**:
  - `entity_id` (TEXT NOT NULL): FOREIGN KEY references `entities(id)` ON DELETE CASCADE.
  - `chunk_id` (TEXT NOT NULL): FOREIGN KEY references `chunks(id)` ON DELETE CASCADE.
- **Indices**:
  - `idx_mentions_entity` ON `entity_mentions(entity_id)` (Visited entity lookup index).
  - `idx_mentions_chunk` ON `entity_mentions(chunk_id)` (Relevance scoring index).

### 1.6 Table: `relations`
Stores semantic graph edges connecting canonical entities.
- **Fields**:
  - `id` (TEXT PRIMARY KEY): Unique identifier.
  - `source_id` (TEXT NOT NULL): Origin node entity ID. FOREIGN KEY references `entities(id)` ON DELETE CASCADE.
  - `target_id` (TEXT NOT NULL): Destination node entity ID. FOREIGN KEY references `entities(id)` ON DELETE CASCADE.
  - `relation_type` (TEXT NOT NULL): Edge description tag (e.g. `"links_to"`, `"member_of"`).
  - `metadata` (TEXT): JSON-stringified dictionary storing relation weights (`{"weight": 1.0}`).
- **Indices**:
  - `idx_relations_source` ON `relations(source_id)` (BFS traversal forward exploration index).
  - `idx_relations_target` ON `relations(target_id)` (BFS traversal backward exploration index).

### 1.7 Table: `artifact_links`
Stores parent-document connectivity graphs.
- **Fields**:
  - `source_artifact_id` (TEXT NOT NULL): FOREIGN KEY references `artifacts(id)` ON DELETE CASCADE.
  - `target_artifact_id` (TEXT NOT NULL): FOREIGN KEY references `artifacts(id)` ON DELETE CASCADE.
- **Indices**:
  - `idx_art_links_src` ON `artifact_links(source_artifact_id)`
  - `idx_art_links_tgt` ON `artifact_links(target_artifact_id)`

### 1.8 Table: `evidence_references`
Tracks provenance mappings for explanation generation.
- **Fields**:
  - `id` (TEXT PRIMARY KEY): Unique identifier.
  - `artifact_id` (TEXT NOT NULL)
  - `chunk_id` (TEXT)
  - `entity_id` (TEXT)
  - `relation_id` (TEXT)
  - `extraction_method` (TEXT NOT NULL)
  - `confidence` (REAL NOT NULL)
  - `timestamp` (TEXT NOT NULL)
