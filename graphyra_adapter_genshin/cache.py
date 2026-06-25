import os
import json
from typing import Dict, Any, List, Optional


class CrawlCache:
    """
    Manages persistent local storage of crawling synchronization state.
    Used for incremental sync to compare revision IDs and track deleted pages.
    """

    def __init__(self, cache_file_path: str):
        self.cache_file_path = cache_file_path
        self.data: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        """Loads cache data from the JSON file if it exists."""
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to parse cache file: {e}. Starting fresh.")
                self.data = {}
        else:
            self.data = {}

    def save(self):
        """Saves current cache state to the JSON file."""
        try:
            # Ensure target parent directories exist
            dir_name = os.path.dirname(self.cache_file_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving crawl cache to '{self.cache_file_path}': {e}")

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached metadata for a specific document ID."""
        return self.data.get(doc_id)

    def set(self, doc_id: str, metadata: Dict[str, Any]):
        """Sets metadata for a document ID and saves cache."""
        self.data[doc_id] = metadata
        self.save()

    def remove(self, doc_id: str):
        """Removes a document from the cache and saves."""
        if doc_id in self.data:
            del self.data[doc_id]
            self.save()

    def list_keys(self) -> List[str]:
        """Returns all cached document IDs."""
        return list(self.data.keys())
