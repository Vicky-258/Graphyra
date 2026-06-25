import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from graphyra.adapters import SourceAdapter
from graphyra.contracts import KnowledgeDocument

from graphyra_adapter_genshin import config
from graphyra_adapter_genshin.cache import CrawlCache
from graphyra_adapter_genshin.mediawiki_client import MediaWikiClient
from graphyra_adapter_genshin.parser import GenshinWikiParser
from graphyra_adapter_genshin.sync import WikiSyncEngine


@dataclass
class AdapterResult:
    documents: List[KnowledgeDocument]
    pages_discovered: int
    pages_processed: int
    pages_new: int
    pages_updated: int
    pages_deleted: int
    failed_pages: List[str] = field(default_factory=list)
    crawl_timestamp: str = ""


class GenshinWikiAdapter(SourceAdapter):
    """
    Orchestrates the discovery, crawling, change detection, and parsing
    of the Genshin Impact Fandom Wiki, producing normalized KnowledgeDocuments.
    """

    def __init__(
        self,
        endpoint_url: str = config.ENDPOINT_URL,
        source_id_prefix: str = config.SOURCE_ID_PREFIX,
        cache_file_path: str = config.CACHE_FILE,
        output_dir: str = config.OUTPUT_DIR
    ):
        self.endpoint_url = endpoint_url
        self.source_id_prefix = source_id_prefix
        self.cache_file_path = cache_file_path
        self.output_dir = output_dir

        self.client = MediaWikiClient(self.endpoint_url, config.USER_AGENT)
        self.parser = GenshinWikiParser(self.source_id_prefix)
        self.cache = CrawlCache(self.cache_file_path)
        self.sync_engine = WikiSyncEngine(self.cache, self.client, self.source_id_prefix)

    def ingest(
        self,
        category: Optional[str] = None,
        max_pages: Optional[int] = None,
        incremental: bool = False
    ) -> AdapterResult:
        """
        Ingests content from the wiki, returning a telemetry-rich AdapterResult.
        Supports full crawling via page enumeration, category limiting, and incremental checks.
        """
        # 1. Discover targets
        if category:
            discovered_titles = self.client.discover_category_members(category, limit=max_pages)
        else:
            discovered_titles = self.client.discover_all_page_titles(limit=max_pages)

        # Deduplicate and sort
        discovered_titles = sorted(list(set(discovered_titles)))

        # Slice to max pages if requested
        if max_pages and len(discovered_titles) > max_pages:
            discovered_titles = discovered_titles[:max_pages]

        # 2. Sync Diff
        if incremental:
            new_pages, updated_pages, deleted_doc_ids, latest_revisions = self.sync_engine.diff(discovered_titles)
        else:
            new_pages = discovered_titles
            updated_pages = []
            deleted_doc_ids = []
            latest_revisions = self.client.get_page_revisions(discovered_titles)

        to_fetch = new_pages + updated_pages
        documents: List[KnowledgeDocument] = []
        failed_pages: List[str] = []
        pages_processed = 0

        # 3. Fetching Loop with Failure Tolerance
        for title in to_fetch:
            try:
                # Fetch parsed HTML details
                parse_data = self.client.fetch_page_parse(title)
                canonical_title = parse_data.get("title", title)
                html_content = parse_data.get("text", {}).get("*", "")
                
                # Parse to KnowledgeDocuments
                extracted_docs = self.parser.parse(html_content, canonical_title)
                documents.extend(extracted_docs)

                # Set cache status revision metadata on successful parse
                doc_id = f"{self.source_id_prefix}:{canonical_title.replace(' ', '_')}"
                if canonical_title in latest_revisions:
                    self.cache.set(doc_id, latest_revisions[canonical_title])
                elif title in latest_revisions:
                    self.cache.set(doc_id, latest_revisions[title])
                else:
                    # Fallback default mock revision if missing
                    self.cache.set(doc_id, {"revid": 1, "timestamp": datetime.datetime.now().isoformat()})

                pages_processed += 1
            except Exception as e:
                # Page processing failures must NOT abort the crawling run
                print(f"Error: Ingest failed for page '{title}': {e}")
                failed_pages.append(title)

        # Clean up deleted documents from cache
        if incremental:
            for doc_id in deleted_doc_ids:
                self.cache.remove(doc_id)

        return AdapterResult(
            documents=documents,
            pages_discovered=len(discovered_titles),
            pages_processed=pages_processed,
            pages_new=len(new_pages),
            pages_updated=len(updated_pages),
            pages_deleted=len(deleted_doc_ids),
            failed_pages=failed_pages,
            crawl_timestamp=datetime.datetime.now().isoformat()
        )

    def ingest_pages(self, titles: List[str], incremental: bool = False) -> AdapterResult:
        """
        Ingests a specific list of pages (primarily for debugging/testing), returning an AdapterResult.
        """
        discovered_titles = sorted(list(set(titles)))

        # Sync Diff
        if incremental:
            new_pages, updated_pages, deleted_doc_ids, latest_revisions = self.sync_engine.diff(discovered_titles)
        else:
            new_pages = discovered_titles
            updated_pages = []
            deleted_doc_ids = []
            latest_revisions = self.client.get_page_revisions(discovered_titles)

        to_fetch = new_pages + updated_pages
        documents: List[KnowledgeDocument] = []
        failed_pages: List[str] = []
        pages_processed = 0

        # Fetching Loop with Failure Tolerance
        for title in to_fetch:
            try:
                parse_data = self.client.fetch_page_parse(title)
                canonical_title = parse_data.get("title", title)
                html_content = parse_data.get("text", {}).get("*", "")
                
                extracted_docs = self.parser.parse(html_content, canonical_title)
                documents.extend(extracted_docs)

                # Set cache status revision metadata on successful parse
                doc_id = f"{self.source_id_prefix}:{canonical_title.replace(' ', '_')}"
                if canonical_title in latest_revisions:
                    self.cache.set(doc_id, latest_revisions[canonical_title])
                elif title in latest_revisions:
                    self.cache.set(doc_id, latest_revisions[title])
                else:
                    self.cache.set(doc_id, {"revid": 1, "timestamp": datetime.datetime.now().isoformat()})

                pages_processed += 1
            except Exception as e:
                print(f"Error: Ingest failed for page '{title}': {e}")
                failed_pages.append(title)

        if incremental:
            for doc_id in deleted_doc_ids:
                self.cache.remove(doc_id)

        return AdapterResult(
            documents=documents,
            pages_discovered=len(discovered_titles),
            pages_processed=pages_processed,
            pages_new=len(new_pages),
            pages_updated=len(updated_pages),
            pages_deleted=len(deleted_doc_ids),
            failed_pages=failed_pages,
            crawl_timestamp=datetime.datetime.now().isoformat()
        )

    def ingest_page(self, title: str) -> AdapterResult:
        """Forces crawl parsing of a single page bypassing cache lookup, returning telemetry."""
        return self.ingest_pages([title], incremental=False)

    def parse_html(self, html_content: str, title: str) -> List[KnowledgeDocument]:
        """Provides raw HTML parsing, completely isolated from network or cached storage."""
        return self.parser.parse(html_content, title)
