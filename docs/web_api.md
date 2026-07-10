# Web Server & REST APIs

Graphyra's backend server is implemented in `server.py` inside the sibling `Graphyra-Wrappers` project repository. It serves UI static assets, exposes HTTP REST API query endpoints, calculates coverage statistics, and coordinates asynchronous crawl jobs.

---

## 1. REST API Endpoint Specifications

### 1.1 `POST /api/query`
Executes entity/semantic seed discovery, BFS graph traversal, path scoring, and evidence collection.

* **Request Body (JSON)**:
  ```json
  {
    "q": "Show connections for Entity A?",
    "max_depth": 2,
    "enable_scoring": true
  }
  ```
* **Response Body (JSON)**:
  ```json
  {
    "question": "Show connections for Entity A?",
    "entities": [
      {
        "id": "ENT_001",
        "canonical_name": "Entity A",
        "entity_type": "CONCEPT",
        "metadata": {}
      }
    ],
    "seed_anchors": [
      {
        "id": "ENT_001",
        "canonical_name": "Entity A",
        "entity_type": "CONCEPT"
      }
    ],
    "discovered_paths": [
      {
        "seed": "ENT_001",
        "target": "ENT_002",
        "hops": ["ENT_001", "ENT_002"],
        "relations": ["links_to"],
        "score": 0.95,
        "depth": 1
      }
    ],
    "chunks": [
      {
        "id": "CHK_001",
        "artifact_id": "ART_001",
        "content": "Entity A is a canonical example of...",
        "metadata": {
          "best_traversal_score": 0.95,
          "min_depth": 1,
          "discovered_by": ["ENT_001"]
        }
      }
    ],
    "diagnostics": {
      "latency_ms": 12
    }
  }
  ```

---

### 1.2 `POST /api/crawl`
Spawns an asynchronous background crawl and sync job to scrape wiki source pages.

* **Request Body (JSON)**:
  ```json
  {
    "limit": 100
  }
  ```
* **Response Body (JSON)**:
  ```json
  {
    "job_id": "JOB_1782695986634",
    "status": "queued",
    "message": "Crawl job has been successfully queued."
  }
  ```

---

### 1.3 `GET /api/status`
Retrieves execution status, progress metrics, and errors of a background crawl job.
* **Query Parameters**: `?job_id=JOB_1782695986634`
* **Response Body (JSON)**:
  ```json
  {
    "job_id": "JOB_1782695986634",
    "status": "completed",
    "progress": 100.0,
    "message": "Successfully ingested 100 pages and indexed semantic embeddings.",
    "error": null,
    "metrics": {
      "pages_crawled": 100,
      "chunks_created": 435,
      "anchors_resolved": 112,
      "relations_created": 512
    }
  }
  ```

---

### 1.4 `GET /api/stats`
Computes metrics to show diagnostics, coverage statistics, and alias distributions in the visualizer dashboard.
* **Response Body (JSON)**:
  ```json
  {
    "total_pages": 486,
    "total_chunks": 2341,
    "total_entities": 412,
    "total_relations": 2841,
    "anchor_coverage_pct": 100.0,
    "entity_histogram": {
      "0": 12,
      "1": 341,
      "2-5": 52,
      "6+": 7
    }
  }
  ```

---

### 1.5 `POST /api/reset`
Wipes all database tables in `graphyra.db` and resets the SQLite vector database index `embeddings.db`, resetting the application state.
* **Response Body (JSON)**:
  ```json
  {
    "status": "success",
    "message": "Knowledge graph storage and semantic vector indexes have been successfully reset."
  }
  ```

---

## 2. Background Job Runner & Thread Pools

To execute crawls without blocking main HTTP request threads:
* **`JobRegistry` / `JobManager`**: Defined in [jobs.py](../graphyra/utils/jobs.py). Coordinates a background thread pool containing worker threads.
* **Crawl Workers**: Scrape the wiki, parse DOM elements, build relational artifact tables inside `graphyra.db`, and trigger the bootstrapped semantic `EmbeddingIndexer` to sync vectors into `embeddings.db`.
* **State Persistence**: Job objects reside in memory and update progress metrics dynamically (e.g. `0%` to `100%`), which are polled periodically by the browser client dashboard.
