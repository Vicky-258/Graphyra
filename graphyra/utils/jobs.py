import uuid
import datetime
import threading
import traceback
from dataclasses import dataclass, field
from typing import Dict, Any, List
from graphyra.storage.sqlite_storage import SQLiteStorage
from graphyra.ingestion.pipeline import IngestionPipeline
from graphyra.ingestion.mention_extractor import DictionaryMentionExtractor
from graphyra.interfaces.models import KnowledgeDocument, Section, ContentBlock, Reference


@dataclass
class JobInfo:
    id: str
    status: str = "pending"
    progress: float = 0.0
    message: str = "Job initialized."
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        "artifacts_created": 0,
        "chunks_created": 0,
        "relations_created": 0,
        "mentions_extracted": 0,
        "anchors_resolved": 0,
        "duration": 0.0
    })
    error: str = ""
    created_at: str = ""
    completed_at: str = ""


class JobRegistry:
    _jobs: Dict[str, JobInfo] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, job: JobInfo):
        with cls._lock:
            cls._jobs[job.id] = job

    @classmethod
    def get(cls, job_id: str) -> JobInfo:
        with cls._lock:
            return cls._jobs.get(job_id)

    @classmethod
    def list_all(cls) -> List[JobInfo]:
        with cls._lock:
            return list(cls._jobs.values())


class JobManager:

    @staticmethod
    def submit_crawl_job(storage: SQLiteStorage) -> str:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = JobInfo(
            id=job_id,
            status="pending",
            progress=0.0,
            message="Initializing background crawl job...",
            created_at=datetime.datetime.now().isoformat()
        )
        JobRegistry.register(job)

        # Spawn execution in a background thread
        thread = threading.Thread(
            target=JobManager._execute_crawl_job,
            args=(job_id, storage)
        )
        thread.daemon = True
        thread.start()

        return job_id

    @staticmethod
    def _execute_crawl_job(job_id: str, storage: SQLiteStorage):
        job = JobRegistry.get(job_id)
        if not job:
            return

        job.status = "running"
        job.progress = 5.0
        job.message = "Clearing existing database and crawl caches..."

        try:
            # 1. Truncate all database tables (dump handcrafted pages)
            with storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM relations")
                cursor.execute("DELETE FROM chunks")
                cursor.execute("DELETE FROM artifacts")
                cursor.execute("DELETE FROM entity_mentions")
                cursor.execute("DELETE FROM aliases")
                cursor.execute("DELETE FROM entities")
                cursor.execute("DELETE FROM artifact_links")
                cursor.execute("DELETE FROM evidence_references")
                conn.commit()

            # 2. Clear sync cache file
            import os
            cache_file = "genshin_crawl_cache.json"
            if os.path.exists(cache_file):
                os.remove(cache_file)

            job.progress = 10.0
            job.message = "Loading source crawler adapter..."

            import importlib
            adapter_class = None
            try:
                adapter_module = importlib.import_module("graphyra_adapter_genshin.adapter")
                adapter_class = getattr(adapter_module, "GenshinWikiAdapter")
            except (ImportError, AttributeError):
                pass

            if not adapter_class:
                raise NotImplementedError(
                    "No crawler adapter module is installed or configured in the system. "
                    "Graphyra is running in standalone local repository mode."
                )

            import threading
            adapter = adapter_class()
            
            mode = adapter.crawler_config.get("mode", "full")
            seed_pages = adapter.crawler_config.get("seed_pages", [])
            max_pages = adapter.crawler.max_pages

            if mode != "seeded" or not seed_pages:
                # Standard discovery list
                discovered_titles = adapter.client.discover_all_page_titles(limit=max_pages)
                discovered_titles = sorted(list(set(discovered_titles)))
            else:
                discovered_titles = seed_pages

            job.message = f"Starting crawl (mode={mode}, max_pages={max_pages}). Discovered {len(discovered_titles)} initial pages."
            job.progress = 15.0

            processed_lock = threading.Lock()
            processed_count = 0
            
            def progress_cb(current, total, title):
                nonlocal processed_count
                with processed_lock:
                    processed_count = current
                    progress_val = 15.0 + (processed_count / total) * 45.0
                    job.progress = min(60.0, round(progress_val, 1))
                    job.message = f"Downloaded page {processed_count}/{total}: '{title}'..."

            # Execute Crawl via WikiCrawler
            crawl_results = adapter.crawler.crawl(
                mode=mode,
                seed_pages=seed_pages,
                all_titles_fallback=discovered_titles if mode != "seeded" else None,
                progress_callback=progress_cb
            )

            # Get revision metadata for downloaded pages
            downloaded_titles = [title for title, _ in crawl_results]
            latest_revisions = adapter.client.get_page_revisions(downloaded_titles)

            documents = []
            cache_updates = []
            
            total_pages = len(crawl_results)
            for idx, (title, parse_data) in enumerate(crawl_results):
                if idx % 50 == 0 and idx > 0:
                    job.progress = 60.0 + (idx / total_pages) * 10.0
                    job.message = f"Parsing HTML and normalizing pages: {idx}/{total_pages}..."
                    print(f"[Crawl Job] Parsing HTML and normalizing pages: {idx}/{total_pages}...", flush=True)
                try:
                    canonical_title = parse_data.get("title", title)
                    html_content = parse_data.get("text", {}).get("*", "")
                    
                    extracted_docs = adapter.parser.parse(html_content, canonical_title, parse_data.get("redirects", []))
                    documents.extend(extracted_docs)
                    
                    doc_id = f"{adapter.source_id_prefix}:{canonical_title.replace(' ', '_')}"
                    revision_info = latest_revisions.get(canonical_title) or latest_revisions.get(title)
                    rev_info = revision_info if revision_info else {"revid": 1, "timestamp": datetime.datetime.now().isoformat()}
                    cache_updates.append((doc_id, rev_info))
                except Exception as page_err:
                    print(f"Warning: Failed to parse page '{title}': {page_err}", flush=True)

            # Sequentially update persistent cache file in main thread
            for doc_id, rev_info in cache_updates:
                adapter.cache.data[doc_id] = rev_info
            adapter.cache.save()

            job.progress = 60.0
            job.message = "Crawl finished. Configuring pipeline mention extractor vocabulary..."
            
            # Setup Pipeline with Extractor populated with vocabulary of titles
            vocabulary = {"Nahida", "Rukkhadevata", "Irminsul", "Sumeru", "Sumeru Akademiya", "Traveler", "Akasha System", "Forbidden Knowledge", "Il Dottore", "Dottore"}
            for doc in documents:
                vocabulary.add(doc.title)
                
            extractor = DictionaryMentionExtractor(vocabulary)
            pipeline = IngestionPipeline(storage, extractor)

            # Define pipeline progress callback to update job progress/message dynamically
            def pipeline_progress_cb(progress_pct, msg):
                job.progress = progress_pct
                job.message = msg

            # Run Ingestion
            pipeline_metrics = pipeline.ingest_documents(documents, progress_callback=pipeline_progress_cb)

            # Ingest Semantic Embeddings for newly created chunks
            job.progress = 99.0
            job.message = "Ingestion complete. Constructing semantic embeddings index..."
            print("[Crawl Job] Ingestion complete. Running semantic indexer...", flush=True)
            
            try:
                from graphyra.semantic.bootstrap import bootstrap_semantic_layer
                _, _, _, indexer = bootstrap_semantic_layer(storage, db_path="embeddings.db")
                indexer.verify_and_rebuild_if_needed()
                indexed_count = indexer.index_missing_chunks()
                print(f"[Crawl Job] Successfully indexed {indexed_count} new chunks.", flush=True)
            except Exception as sem_err:
                print(f"[Crawl Job] Warning: Semantic indexing failed: {sem_err}", flush=True)
                traceback.print_exc()

            job.progress = 100.0
            job.status = "completed"
            job.message = f"Successfully ingested {len(documents)} pages and indexed semantic embeddings."
            job.metrics = pipeline_metrics
            job.completed_at = datetime.datetime.now().isoformat()

        except Exception as e:
            job.status = "failed"
            job.error = f"{str(e)}\n{traceback.format_exc()}"
            job.message = "Job failed during crawl/ingestion."
            job.completed_at = datetime.datetime.now().isoformat()

    @staticmethod
    def _load_local_corpus_documents(corpus_path: str) -> List[KnowledgeDocument]:
        import json
        with open(corpus_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        for item in data:
            title = item["title"]
            entity_type = item["entity_type"]
            source_type = item.get("source_type", "handcrafted")
            source = item.get("source", "sumeru_lore")
            content = item["content"]
            outgoing_links = item.get("outgoing_links", [])

            # Wrap content in content block and Section
            section = Section(
                id="main",
                title="Main",
                content_blocks=[ContentBlock(type="text", content=content)]
            )

            # Map references to target document stable format IDs
            references = []
            for target in outgoing_links:
                ref = Reference(
                    source_document=title,
                    source_anchor=target,
                    target_document=f"genshin_fandom:main:{target.lower().replace(' ', '_')}",
                    target_anchor=target,
                    reference_type="links_to"
                )
                references.append(ref)

            doc_id = f"genshin_fandom:main:{title.lower().replace(' ', '_')}"
            doc = KnowledgeDocument(
                id=doc_id,
                title=title,
                source_type=source_type,
                metadata={"entity_type": entity_type, "source": source},
                sections=[section],
                references=references
            )
            docs.append(doc)
        return docs
