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

# Crawler integration
from graphyra_adapter_genshin.config_loader import load_crawler_config
from graphyra.crawler import CrawlerFilter, WikiCrawler


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
        output_dir: str = config.OUTPUT_DIR,
        crawler_config: Optional[Dict[str, Any]] = None
    ):
        self.endpoint_url = endpoint_url
        self.source_id_prefix = source_id_prefix
        self.cache_file_path = cache_file_path
        self.output_dir = output_dir

        self.client = MediaWikiClient(self.endpoint_url, config.USER_AGENT)
        self.parser = GenshinWikiParser(self.source_id_prefix)
        self.cache = CrawlCache(self.cache_file_path)
        self.sync_engine = WikiSyncEngine(self.cache, self.client, self.source_id_prefix)

        # Ingestion configurations loading
        self.crawler_config = crawler_config or load_crawler_config()
        self.crawler_filter = CrawlerFilter(self.crawler_config)
        max_p = self.crawler_config.get("max_pages", 500)
        self.crawler = WikiCrawler(self.client, self.crawler_filter, max_pages=max_p)

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
        if max_pages is not None:
            self.crawler.max_pages = max_pages

        mode = self.crawler_config.get("mode", "full")
        seed_pages = self.crawler_config.get("seed_pages", [])

        # 1. Discover initial targets
        all_titles_fallback = []
        if mode != "seeded" or not seed_pages:
            if category:
                all_titles_fallback = self.client.discover_category_members(category, limit=max_pages)
            else:
                all_titles_fallback = self.client.discover_all_page_titles(limit=max_pages)
            all_titles_fallback = sorted(list(set(all_titles_fallback)))

        # 2. Run crawl stage through configured Crawler
        crawl_results = self.crawler.crawl(
            mode=mode,
            seed_pages=seed_pages,
            all_titles_fallback=all_titles_fallback
        )

        discovered_titles = [title for title, _ in crawl_results]

        # 3. Sync Diff check
        if incremental:
            new_pages, updated_pages, deleted_doc_ids, latest_revisions = self.sync_engine.diff(discovered_titles)
            to_fetch_set = set(new_pages + updated_pages)
        else:
            new_pages = discovered_titles
            updated_pages = []
            deleted_doc_ids = []
            to_fetch_set = set(discovered_titles)
            latest_revisions = self.client.get_page_revisions(discovered_titles)

        documents: List[KnowledgeDocument] = []
        failed_pages: List[str] = [t for t, r in self.crawler.skip_reasons.items() if "Download failure" in r]
        pages_processed = 0

        # 4. Parse content
        for title, parse_data in crawl_results:
            if title not in to_fetch_set:
                continue
            try:
                canonical_title = parse_data.get("title", title)
                html_content = parse_data.get("text", {}).get("*", "")

                extracted_docs = self.parser.parse(html_content, canonical_title, parse_data.get("redirects", []))
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

        # Clean up deleted documents from cache
        if incremental:
            for doc_id in deleted_doc_ids:
                self.cache.remove(doc_id)

        # Output detailed crawler telemetry report
        print(f"\n--- Crawler Run Report ---")
        print(f"Total Pages Discovered: {self.crawler.total_discovered}")
        print(f"Pages Accepted: {self.crawler.accepted_count}")
        print(f"Pages Skipped: {self.crawler.skipped_count}")
        if self.crawler.skip_reasons:
            print("Skip Reasons (sample of 10):")
            for t, r in list(self.crawler.skip_reasons.items())[:10]:
                print(f"  - '{t}': {r}")

        return AdapterResult(
            documents=documents,
            pages_discovered=self.crawler.total_discovered,
            pages_processed=pages_processed,
            pages_new=len([t for t in to_fetch_set if t in discovered_titles]),
            pages_updated=0,
            pages_deleted=len(deleted_doc_ids) if incremental else 0,
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

                extracted_docs = self.parser.parse(html_content, canonical_title, parse_data.get("redirects", []))
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
