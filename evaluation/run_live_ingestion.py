import os
import time
import datetime
import traceback
import importlib
import sqlite3

# Local imports
from storage.sqlite_storage import SQLiteStorage
from ingestion.pipeline import IngestionPipeline
from ingestion.mention_extractor import DictionaryMentionExtractor


def run_rebuild():
    db_file = "graphyra.db"
    emb_db = "embeddings.db"
    
    print("--- STARTING GRAPHREBUILD FOR 1,000 PAGES ---")
    print(f"Relational DB: {db_file}")
    print(f"Embedding DB: {emb_db}")
    
    storage = SQLiteStorage(db_file)
    storage.initialize_database()
    
    # 1. Truncate all tables
    print("Truncating database tables...")
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
        
    # 2. Clear sync cache and temporary files
    cache_file = "genshin_crawl_cache.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print("Cleared crawl cache file.")
        
    if os.path.exists(emb_db):
        os.remove(emb_db)
        print("Cleared embeddings database file to rebuild from scratch.")
        
    # 3. Load adapter
    print("Loading crawler adapter...")
    adapter_module = importlib.import_module("graphyra_adapter_genshin.adapter")
    adapter_class = getattr(adapter_module, "GenshinWikiAdapter")
    adapter = adapter_class()
    
    mode = adapter.crawler_config.get("mode", "full")
    seed_pages = adapter.crawler_config.get("seed_pages", [])
    max_pages = adapter.crawler.max_pages
    
    print(f"Crawl configuration loaded: mode={mode}, max_pages={max_pages}")
    
    if mode != "seeded" or not seed_pages:
        discovered_titles = adapter.client.discover_all_page_titles(limit=max_pages)
        discovered_titles = sorted(list(set(discovered_titles)))
    else:
        discovered_titles = seed_pages
        
    print(f"Discovered {len(discovered_titles)} starting pages. Triggering crawler...")
    
    t0 = time.time()
    
    # Run crawl
    crawl_results = adapter.crawler.crawl(
        mode=mode,
        seed_pages=seed_pages,
        all_titles_fallback=discovered_titles if mode != "seeded" else None,
        progress_callback=lambda current, total, title: print(f"Downloaded page {current}/{total}: '{title}'...", flush=True)
    )
    
    print(f"Crawler finished. Downloaded {len(crawl_results)} pages in {time.time() - t0:.2f} seconds.")
    
    # Parse html to documents
    print("Parsing HTML and extracting KnowledgeDocuments...")
    downloaded_titles = [title for title, _ in crawl_results]
    latest_revisions = adapter.client.get_page_revisions(downloaded_titles)
    
    documents = []
    cache_updates = []
    total_pages = len(crawl_results)
    
    for idx, (title, parse_data) in enumerate(crawl_results):
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
            print(f"Warning: Failed to parse page '{title}': {page_err}")
            
    # Save cache
    for doc_id, rev_info in cache_updates:
        adapter.cache.data[doc_id] = rev_info
    adapter.cache.save()
    
    print(f"Parsed {len(documents)} documents successfully.")
    
    # Mention extractor setup
    vocabulary = {"Nahida", "Rukkhadevata", "Irminsul", "Sumeru", "Sumeru Akademiya", "Traveler", "Akasha System", "Forbidden Knowledge", "Il Dottore", "Dottore"}
    for doc in documents:
        vocabulary.add(doc.title)
        
    extractor = DictionaryMentionExtractor(vocabulary)
    pipeline = IngestionPipeline(storage, extractor)
    
    # Run Ingestion
    print("Running ingestion pipeline (database schema filling)...")
    pipeline_metrics = pipeline.ingest_documents(
        documents,
        progress_callback=lambda progress, msg: print(f"[Pipeline] {progress}% - {msg}", flush=True)
    )
    print(f"Pipeline Ingestion complete: {pipeline_metrics}")
    
    # Semantic Embeddings Indexing
    print("Indexing semantic embeddings...")
    from semantic.bootstrap import bootstrap_semantic_layer
    _, _, _, indexer = bootstrap_semantic_layer(storage, db_path=emb_db)
    indexer.verify_and_rebuild_if_needed()
    indexed_count = indexer.index_missing_chunks()
    print(f"Semantic Indexer complete. Indexed {indexed_count} new chunks.")
    print(f"Total time elapsed: {time.time() - t0:.2f} seconds.")


if __name__ == "__main__":
    run_rebuild()
