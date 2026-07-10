# ADR 001: Domain-Agnostic Graphyra Core

## Status
Accepted

## Context
Originally, the Graphyra retrieval codebase was tightly coupled to MediaWiki structures and the Sumeru/Genshin wiki domain vocabulary (e.g. character names, display title rewrites, Akasha, Irminsul, Nahida, Rukkhadevata). This made it difficult to extend the engine to new domains like API methods, research papers, legal statutes, or Markdown files.

## Decision
Establish complete domain agnosticism in Graphyra Core. All domain-specific concepts, parsing, crawlers, and transformations must live outside Core in adapter packages (e.g. `graphyra-adapter-genshin`). Core only receives normalized `KnowledgeDocument` structures and generic ingestion directives. 

We enforce this programmatically via automated architectural compliance tests that prevent sibling adapter imports or hardcoded domain terms inside Core.

## Consequences
- Core becomes a generic framework suitable for any heterogeneous graph retrieval task.
- New adapters can be written without editing Graphyra Core.
- Adapter logic is strictly isolated from core traversal, semantic retrieval, and ranking algorithms.
