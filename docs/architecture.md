# Graphyra — System Architecture & Topology

This document describes the high-level system topology, data boundaries, and query execution life cycle of Graphyra V1.

---

## 1. Architectural Boundaries

Graphyra separates the ingestion of raw, external source content from the representation of entities and relations. The system is split into two principal parts:

1. **External Source Adapter** (`graphyra-adapter-genshin`): Scrapes external sites (e.g. Genshin Fandom Wiki), parses raw HTML DOM tables and paragraphs, and constructs standard `KnowledgeDocument` containers.
2. **Graphyra Core** (`Graphyra`): Receives the standard `KnowledgeDocument`, performs paragraph segmentation, extracts entity mentions, maps synonym aliases, creates graph relations, indexes vector semantics, and resolves traversals.

```text
External Source (Wiki)
        │
        ▼
[graphyra-adapter-genshin]  <--- Scraping & parsing boundaries
        │
        │  Produce KnowledgeDocument
        ▼
KnowledgeDocument           <--- Interface boundary
        │
        ▼
[Graphyra Core]             <--- Graph & Traversal boundaries
   ├── Artifact Creation
   ├── Paragraph-First Chunking
   ├── Mention Extraction
   ├── Alias / Anchor Resolution
   ├── Relation / Link Construction
   └── Traversal & Semantic Retrieval
```

---

## 2. Core System Topology

Graphyra operates on two distinct databases to keep knowledge graphs isolated from machine learning derivations:
1. **Knowledge Graph DB** (`graphyra.db`): The relational truth store containing pages (artifacts), text chunks, entities (anchors), synonym aliases, entity mentions, and structural links.
2. **Semantic Vector Index** (`embeddings.db`): A decoupled vector index storage mapping chunk IDs to floating-point embedding arrays. It acts as an auxiliary candidate discovery layer.

```text
               +--------------------------------------+
               |          Client Visualizer           |
               +------------------+-------------------+
                                  |
                                  | HTTP REST API
                                  v
               +------------------+-------------------+
               |        web server (server.py)        |
               +--------+--------------------+--------+
                        |                    |
                        | Query              | Crawl & Sync Job
                        v                    v
               +--------+---------+  +-------+--------+
               |  Graphyra Engine |  | Ingestion      |
               |    (engine.py)   |  | Pipeline       |
               +---+-----------+--+  +-------+--------+
                   |           |             |
                   |           |             | Incremental Sync
                   |           v             v
                   |     +-----+-------------+----+
                   |     |    EmbeddingIndexer    |
                   |     +-----------+------------+
                   |                 |
                   v                 v
          +--------+--------+  +-----+------------+
          | Knowledge Graph |  |  SQLiteVector    |
          |       DB        |  |     Index        |
          |  (graphyra.db)  |  | (embeddings.db)  |
          +-----------------+  +------------------+
```

---

## 3. Query Sequence Flow

When a query is received at `/api/query`, it triggers parallel candidate discovery, DTO fusion, graph traversal, and subgraph formatting.

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Browser
    participant API as Server (server.py)
    participant Core as Graphyra Engine (engine.py)
    participant Sem as SQLiteVectorIndex (index.py)
    participant Fusion as CandidateFusionEngine (fusion.py)
    participant Trav as TraversalEngine (traversal_engine.py)
    participant Evid as EvidenceRetriever (evidence_retriever.py)
    participant Sub as SubgraphBuilder (subgraph_builder.py)

    Client->>API: HTTP POST /api/query {"q": "Who is Nahida?"}
    API->>Core: retrieve(question)
    
    rect rgb(230, 245, 255)
        note right of Core: Parallel Candidate Discovery (Day 6)
        par Exact Entity Check
            Core->>Core: Match canonical names & aliases in text
        and Vector Semantic Lookup
            Core->>Sem: search(query_vector)
            Sem-->>Core: List[SearchResult] (chunk_id, traversal_score)
            Core->>Core: Extract mentions in top chunks via DictionaryExtractor
        end
    end
    
    Core->>Fusion: fuse_candidates(direct_entities, semantic_entities)
    Fusion-->>Core: List[Tuple[Entity, score]] (fused ranked seeds)
    
    Core->>Trav: traverse(TraversalRequest)
    Note over Trav: BFS graph path search & scoring
    Trav-->>Core: TraversalResult (visited_nodes, discovered_paths)
    
    Core->>Evid: retrieve_evidence(TraversalResult)
    Note over Evid: Wrap chunks in CandidateEvidence DTOs with path scores
    Evid-->>Core: List[CandidateEvidence] (evidence pool)
    
    Core->>Sub: extract(TraversalResult, CandidateEvidence)
    Sub-->>Core: ReasoningSubgraph
    
    Core-->>API: JSON payload {entities, chunks, paths}
    API-->>Client: HTTP 200 Response
```
