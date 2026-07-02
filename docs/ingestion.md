# Ingestion Subsystem

The Ingestion Subsystem segments incoming documents, identifies entity occurrences, registers aliases, and builds structural links.

---

## 1. Paragraph-First Chunking

Rather than arbitrary sentence splitting, Graphyra uses a **Paragraph-First** chunking strategy defined in [ingestion/chunking.py](file:///home/vicky/v_drive/Codes/Graphyra/ingestion/chunking.py) under the `ChunkPolicy` class. 

### Chunking Design Rules:
1. **Paragraph Unity**: Paragraphs are treated as the atomic semantic unit. Split lines are grouped together until they reach a target length (default `500` characters).
2. **Table Preservation**: Multi-row HTML tables (`<table>`) are grouped and extracted as a single, contiguous block so that row-wise context is not severed by splits.
3. **Hard Bounds**: If a single paragraph is excessively long, it is split on sentence punctuation boundaries (`.`, `!`, `?`) using quote-aware regex.
4. **Target Size**: A target chunk size of `500` characters is targeted, with a maximum chunk limit of `1000` characters.

### Key Classes:
* `ChunkPolicy`: Holds parameters (target size, max size, chunk overlap) and exposes `split_text_by_paragraphs(text)` to produce content segments.

---

## 2. Mention Extraction Strategy

Graphyra implements the Strategy Pattern to find entity names in text without coupling extraction logic to specific algorithms:

```text
               +--------------------------------------+
               |          MentionExtractor            |
               |             (interface)              |
               +------------------+-------------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
+-----------------------+                   +-----------------------+
|  RegexMentionExtractor|                   |DictionaryMentionExtr. |
| (Regex exact matches) |                   | (Boundary token dict) |
+-----------------------+                   +-----------------------+
```

### Extraction Implementations:
1. **RegexMentionExtractor**: Uses compiled regex patterns to extract canonical entity names directly.
2. **DictionaryMentionExtractor** (Introduced Day 5): Loaded with a vocabulary of known terms (canonical names + all aliases). Uses compiled word boundaries (`\b`) to match multi-word and special-character entity aliases safely:
   ```python
   # Token boundary regex formulation
   pattern = r"\b(" + "|".join(re.escape(name) for name in vocab) + r")\b"
   ```

---

## 3. Synonym Resolution & Redirects

Synonyms and redirects are resolved dynamically during ingestion inside [ingestion/pipeline.py](file:///home/vicky/v_drive/Codes/Graphyra/ingestion/pipeline.py) and [storage/anchor_resolver.py](file:///home/vicky/v_drive/Codes/Graphyra/storage/anchor_resolver.py):

* **SYNONYM / REDIRECT Relations**: When an alias points to a primary entity, it is registered in the database `aliases` table. 
* **Synonym Expansion**: If a synonym match is detected, the resolver maps it to the primary canonical entity, ensuring a single unified node representation in the knowledge graph.
* **Synonym Links**: If Page A references Synonym B which resolves to Entity C, the relationship is mapped as `(Page A) --[mentions]--> (Entity C)`, preventing orphan nodes.

---

## 4. Ingestion Builders

The [ingestion/builders.py](file:///home/vicky/v_drive/Codes/Graphyra/ingestion/builders.py) module orchestrates model creation:
* `ArtifactBuilder`: Parses incoming `KnowledgeDocument` items, creates parent `Artifact` records, and runs the `ChunkPolicy` to yield database chunks.
* `AnchorExtractor`: Iterates over created chunks, runs the active `MentionExtractor`, resolves names via `AnchorResolver`, and writes records to the `entity_mentions` table.
* `RelationBuilder`: Analyzes hyperlinks and page references, writing structural link records into `artifact_links` and `relations`.
