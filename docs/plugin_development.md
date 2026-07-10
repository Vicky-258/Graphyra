# Plugin Development & Adapters Guide

Adapters are first-class citizens in the Graphyra ecosystem. Because Graphyra Core is strictly domain-agnostic, adapters are responsible for crawling, downloading, scraping, or parsing domain documents and transforming them into normalized `KnowledgeDocument` containers.

---

## 1. Data Processing Topology

An adapter operates outside the core framework boundaries:

```text
  [ External Source ]       (Wikis, APIs, Legal code, Git repository)
          │
          ▼
    [ Custom Adapter ]      (Crawls data, parses HTML/DOM/Markdown/PDF)
          │
          ├─► Generates KnowledgeDocument containers
          │   ├── sections (headings + paragraph ContentBlocks)
          │   ├── references (hyperlink relationships)
          │   └── ingestion_directives (mapping steering)
          ▼
  [ Graphyra Ingestion ]    (Segment, extract, resolve, and index)
```

---

## 2. Interface Definitions

An adapter must implement the base contract `BaseAdapter` defined in `graphyra/interfaces/adapter.py` (if applicable) or provide a callable factory.

### 2.1 The `KnowledgeDocument` Schema

Your adapter compiles scraped items into `KnowledgeDocument` objects:

```python
from graphyra.interfaces.models import KnowledgeDocument, Section, ContentBlock, Reference

doc = KnowledgeDocument(
    id="doc_001",
    title="Example Document Title",
    source_type="wiki",
    metadata={"url": "https://example.com/page1", "author": "Author A"},
    sections=[
        Section(
            id="sec_01",
            title="Introduction",
            content_blocks=[
                ContentBlock(type="text", content="This is paragraph text describing the concept."),
                ContentBlock(type="table", content="<table><tr><td>Key</td><td>Value</td></tr></table>")
            ]
        )
    ],
    references=[
        Reference(
            source_document="doc_001",
            source_anchor="Example Document Title",
            target_document="doc_002",
            target_anchor="Linked Document Title",
            reference_type="links_to"
        )
    ],
    ingestion_directives=IngestionDirectives(
        entity_strategy=EntityStrategy.CREATE,
        artifact_strategy=ArtifactStrategy.CREATE
    )
)
```

### 2.2 Steering Ingestion via `IngestionDirectives`

Adapters tell Graphyra Core how to register anchors and documents using **`IngestionDirectives`**:

1. **`entity_strategy`** (`EntityStrategy`):
   - `CREATE`: Automatically creates a canonical retrieval anchor (Entity) matching the page title, and generates simplified alias names. (Default)
   - `LINK`: Resolves the page to an alternate target anchor (specified in `target_anchor`), adding the page name as an alias redirect. Use this for voice-overs, metadata pages, or subpages.
   - `IGNORE`: Prevents entity anchor creation entirely. Use this for index hubs or category lists.
2. **`artifact_strategy`** (`ArtifactStrategy`):
   - `CREATE`: Ingests the page text segments as searchable database chunks. (Default)
   - `IGNORE`: Prevents page content chunking.
3. **`target_anchor`** (str, optional):
   - Specifies the canonical anchor to bind this document to when using the `LINK` strategy.

---

## 3. Dynamic Plugin Registration

Graphyra provides a pluggable registry inside `graphyra/plugins/registry.py`. You register your adapter during application bootstrap:

```python
from graphyra.plugins.registry import PluginRegistry

# Define your custom adapter class
class WikipediaAdapter:
    def __init__(self, limit=100):
        self.limit = limit
        
    def fetch_documents(self):
        # Scraping logic goes here
        return []

# Register the plugin adapter class with a lookup key
PluginRegistry.register_adapter("wikipedia", WikipediaAdapter)
```

Now, job orchestrators and query managers can load and run crawls generically by calling:

```python
adapter_class = PluginRegistry.get_adapter("wikipedia")
adapter_instance = adapter_class(limit=50)
docs = adapter_instance.fetch_documents()
```

This decoupled registration ensures that Graphyra Core contains no compile-time package dependencies on database loaders or web crawlers.
