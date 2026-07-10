# ADR 003: Core Retrieval Anchors (Artifact & Entity Model)

## Status
Accepted

## Context
Downstream consumers and adapters had mismatched expectations on what a database entity represents. Sibling adapters mixed MediaWiki concepts (Main pages, categories, voiceovers) into the ingestion pipeline, causing semantic retrieval collapse for non-character pages.

## Decision
Graphyra represents all knowledge using two distinct constructs:
1. **Artifact**: A physical document segment or file (e.g. Wiki Page, Code file, PDF Manual).
2. **Entity (Retrieval Anchor)**: A canonical conceptual entity (e.g. Character name, Code Class, Statute Title) extracted from chunks.

Adapters steer this division using generic `IngestionDirectives` (`CREATE`, `LINK`, `IGNORE` entity strategies, and `canonical_target`/`target_anchor` target mappings). Core executes these strategies generically.

## Consequences
- Core database schema remains completely domain-agnostic.
- The separation of source file structure (Artifacts) from conceptual indexing anchors (Entities) resolves namespace conflicts.
