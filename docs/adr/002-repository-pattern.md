# ADR 002: Repository Pattern Database Encapsulation

## Status
Accepted

## Context
Raw SQLite queries, connections, and cursor calls (`sqlite3`, `cursor.execute`) were leaking into high-level business logic modules, including the ingestion pipeline, graph builders, and diagnostics wrappers. This created direct storage dependencies and made storage engines difficult to refactor or mock during testing.

## Decision
All raw SQL database access is strictly confined to the repository layer (`graphyra/storage/`) and the semantic index wrapper (`graphyra/semantic/index.py`). High-level engine components (Traversal, Ingestion, Ranking, Explanation, Visualization) must interact with database tables exclusively through storage-agnostic repository methods.

## Consequences
- Automated compliance tests fail if raw `.execute()` or SQLite imports occur outside storage/semantic folders.
- Testing core business logic becomes database-independent.
- Future transitions to alternate backend stores (e.g. PostgreSQL, Neo4j) are simplified.
