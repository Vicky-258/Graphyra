from typing import List, Dict, Any, Set, Tuple
from graphyra_adapter_genshin.cache import CrawlCache
from graphyra_adapter_genshin.mediawiki_client import MediaWikiClient


class WikiSyncEngine:
    """
    Handles synchronization status diffs.
    Compares discovered page revision metadata against cache history
    to find New, Updated, and Deleted documents.
    """

    def __init__(self, cache: CrawlCache, client: MediaWikiClient, source_id_prefix: str = "genshin_fandom:main"):
        self.cache = cache
        self.client = client
        self.source_id_prefix = source_id_prefix

    def diff(self, discovered_titles: List[str]) -> Tuple[List[str], List[str], List[str], Dict[str, Dict[str, Any]]]:
        """
        Runs change detection.
        Returns:
          - new_pages: List of titles to fetch.
          - updated_pages: List of titles to fetch.
          - deleted_doc_ids: List of document IDs that are no longer present.
          - revision_metadata: Dictionary mapping title -> latest revision info.
        """
        # Discover latest revision states for all targets
        latest_revisions = self.client.get_page_revisions(discovered_titles)

        new_pages: List[str] = []
        updated_pages: List[str] = []
        
        # Build set of discovered doc IDs to identify deleted pages
        discovered_doc_ids: Set[str] = set()

        for title in discovered_titles:
            doc_id = f"{self.source_id_prefix}:{title.replace(' ', '_')}"
            discovered_doc_ids.add(doc_id)

            latest_info = latest_revisions.get(title)
            if not latest_info:
                # If revid retrieval fails, fallback to queueing page as new/modified
                new_pages.append(title)
                continue

            cached_info = self.cache.get(doc_id)
            if not cached_info:
                new_pages.append(title)
            elif cached_info.get("revid") != latest_info["revid"]:
                updated_pages.append(title)

        # Detect deleted articles (cached keys not found in current discovered set)
        deleted_doc_ids: List[str] = []
        for cached_doc_id in self.cache.list_keys():
            if cached_doc_id not in discovered_doc_ids:
                deleted_doc_ids.append(cached_doc_id)

        return new_pages, updated_pages, deleted_doc_ids, latest_revisions
