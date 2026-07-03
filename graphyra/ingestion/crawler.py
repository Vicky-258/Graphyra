import fnmatch
from typing import List, Dict, Any, Tuple, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

class CrawlerFilter:
    """
    Domain-agnostic filter for page titles and namespaces.
    Uses configurable rules (include namespaces, exclude prefixes, exclude patterns).
    """
    def __init__(self, config: Dict[str, Any]):
        self.mode = config.get("mode", "full")
        self.include_namespaces = config.get("include_namespaces", [])
        self.exclude_prefixes = config.get("exclude_prefixes", [])
        self.exclude_patterns = config.get("exclude_patterns", [])

    def should_accept(self, title: str) -> Tuple[bool, str]:
        """
        Determines whether a page should be accepted for ingestion.
        Returns:
            (accepted, reason_or_empty)
        """
        if self.mode == "full":
            return True, ""

        # 1. Namespace validation (if include_namespaces is provided)
        if self.include_namespaces:
            has_colon = ":" in title
            if has_colon:
                prefix = title.split(":", 1)[0]
                if "Main" in self.include_namespaces and prefix in ["Category", "Template", "Help", "User", "Talk", "File", "Wiki", "Module", "MediaWiki"]:
                    return False, f"Namespace '{prefix}' not in include_namespaces"

        # 2. Exclude prefixes
        for prefix in self.exclude_prefixes:
            p_colon = prefix if prefix.endswith(":") else f"{prefix}:"
            if title.startswith(p_colon) or title.startswith(prefix):
                return False, f"Matches exclude prefix '{prefix}'"

        # 3. Exclude glob patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(title, pattern):
                return False, f"Matches exclude pattern '{pattern}'"

        return True, ""


class WikiCrawler:
    """
    Domain-agnostic wiki crawling orchestrator.
    Supports standard filtered crawls and seeded BFS traversal crawls.
    """
    def __init__(self, client, crawler_filter: CrawlerFilter, max_pages: int = 500):
        self.client = client
        self.filter = crawler_filter
        self.max_pages = max_pages
        
        # Telemetry/Reporting
        self.total_discovered = 0
        self.skipped_count = 0
        self.accepted_count = 0
        self.skip_reasons = {}  # page_title -> reason

    def crawl(
        self,
        mode: str,
        seed_pages: Optional[List[str]] = None,
        all_titles_fallback: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Triggers either seeded BFS crawl or standard filtered crawl.
        """
        if mode == "seeded" and seed_pages:
            return self.crawl_seeded(seed_pages, progress_callback)
        else:
            titles = all_titles_fallback or []
            return self.crawl_standard(titles, progress_callback)

    def crawl_seeded(
        self,
        seed_pages: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Performs a seeded breadth-first search (BFS) crawl starting from seed_pages.
        """
        visited = set()
        queue = list(seed_pages)
        results = []
        
        self.total_discovered = len(seed_pages)
        processed_count = 0

        while queue and len(results) < self.max_pages:
            # Determine how many pages to fetch in parallel in the current level of BFS
            level_batch = []
            while queue and len(level_batch) + len(results) < self.max_pages:
                page = queue.pop(0)
                if page not in visited:
                    visited.add(page)
                    
                    accepted, reason = self.filter.should_accept(page)
                    if not accepted:
                        self.skipped_count += 1
                        self.skip_reasons[page] = reason
                        continue
                        
                    level_batch.append(page)
                    
            if not level_batch:
                break

            # Fetch batch in parallel
            fetched_data = []
            with ThreadPoolExecutor(max_workers=min(10, len(level_batch))) as executor:
                futures = {executor.submit(self.client.fetch_page_parse, title): title for title in level_batch}
                for future in as_completed(futures):
                    title = futures[future]
                    try:
                        parse_data = future.result()
                        fetched_data.append((title, parse_data))
                    except Exception as e:
                        self.skipped_count += 1
                        self.skip_reasons[title] = f"Download failure: {e}"

            # Process results, update progress, and extract outgoing links
            for title, parse_data in fetched_data:
                self.accepted_count += 1
                results.append((title, parse_data))
                processed_count += 1
                
                if progress_callback:
                    # Provide progress estimates based on max_pages limit
                    progress_callback(processed_count, self.max_pages, title)

                # Extract links for next BFS level
                links = parse_data.get("links", [])
                for link in links:
                    if link.get("ns") == 0:
                        link_title = link.get("*")
                        if link_title and link_title not in visited:
                            queue.append(link_title)
                            self.total_discovered += 1

        return results

    def crawl_standard(
        self,
        discovered_titles: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Performs standard crawl on a predefined list of page titles, applying filtering.
        """
        self.total_discovered = len(discovered_titles)
        to_fetch = []
        
        for title in discovered_titles:
            accepted, reason = self.filter.should_accept(title)
            if not accepted:
                self.skipped_count += 1
                self.skip_reasons[title] = reason
            else:
                to_fetch.append(title)
                
        # Limit to max_pages
        if self.max_pages and len(to_fetch) > self.max_pages:
            self.skipped_count += len(to_fetch) - self.max_pages
            for title in to_fetch[self.max_pages:]:
                self.skip_reasons[title] = f"Exceeded max_pages limit ({self.max_pages})"
            to_fetch = to_fetch[:self.max_pages]

        results = []
        processed_count = 0
        total_to_fetch = len(to_fetch)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.client.fetch_page_parse, title): title for title in to_fetch}
            for future in as_completed(futures):
                title = futures[future]
                try:
                    parse_data = future.result()
                    self.accepted_count += 1
                    results.append((title, parse_data))
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_to_fetch, title)
                except Exception as e:
                    self.skipped_count += 1
                    self.skip_reasons[title] = f"Download failure: {e}"
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_to_fetch, title)
                    
        return results
