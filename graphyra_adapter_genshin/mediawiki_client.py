import urllib.request
import urllib.parse
import json
from typing import List, Dict, Any, Optional


class MediaWikiClient:
    """
    Communicates with the MediaWiki API to crawl and discover pages,
    track revision meta values, and fetch HTML parse payloads.
    """

    def __init__(self, endpoint_url: str, user_agent: str):
        self.endpoint_url = endpoint_url
        self.user_agent = user_agent

    def _query(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Queries API and parses JSON return payload."""
        url = f"{self.endpoint_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.user_agent}
        )
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"HTTP call to MediaWiki API failed: {e}")

    def discover_all_page_titles(self, namespace: int = 0, limit: Optional[int] = None) -> List[str]:
        """Crawls all pages in a given namespace using API pagination continue tokens."""
        titles: List[str] = []
        apcontinue: Optional[str] = None

        while True:
            params = {
                "action": "query",
                "list": "allpages",
                "apnamespace": str(namespace),
                "aplimit": "500",
                "format": "json"
            }
            if apcontinue:
                params["apcontinue"] = apcontinue

            data = self._query(params)
            query_data = data.get("query", {})
            for page in query_data.get("allpages", []):
                t = page.get("title")
                if t:
                    titles.append(t)
                    if limit and len(titles) >= limit:
                        return titles[:limit]

            apcontinue = data.get("continue", {}).get("apcontinue")
            if not apcontinue:
                break

        return titles

    def discover_category_members(self, category_title: str, limit: Optional[int] = None) -> List[str]:
        """Fetches all main namespace members inside a specific Category folder."""
        titles: List[str] = []
        cmcontinue: Optional[str] = None
        
        # Ensure prefix format matches API expectations
        cat_title = category_title
        if not cat_title.startswith("Category:"):
            cat_title = f"Category:{cat_title}"

        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat_title,
                "cmlimit": "500",
                "format": "json"
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            data = self._query(params)
            query_data = data.get("query", {})
            for member in query_data.get("categorymembers", []):
                # ns 0 corresponds to standard article content pages
                if member.get("ns") == 0:
                    t = member.get("title")
                    if t:
                        titles.append(t)
                        if limit and len(titles) >= limit:
                            return titles[:limit]

            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break

        return titles

    def get_page_revisions(self, titles: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetches the latest revision ID and timestamp for a list of pages.
        Divides titles in batches of 50 to avoid HTTP query length issues.
        """
        results: Dict[str, Dict[str, Any]] = {}
        if not titles:
            return results

        for i in range(0, len(titles), 50):
            batch = titles[i:i+50]
            params = {
                "action": "query",
                "prop": "revisions",
                "titles": "|".join(batch),
                "rvprop": "ids|timestamp",
                "format": "json"
            }
            try:
                data = self._query(params)
                pages_data = data.get("query", {}).get("pages", {})
                for page_id, info in pages_data.items():
                    title = info.get("title")
                    revisions = info.get("revisions", [])
                    if title and revisions:
                        latest = revisions[0]
                        results[title] = {
                            "revid": latest.get("revid"),
                            "timestamp": latest.get("timestamp")
                        }
            except Exception as e:
                # Log error silently and continue with other query batches
                print(f"Warning: Failed to fetch revisions metadata: {e}")

        return results

    def fetch_page_parse(self, title: str) -> Dict[str, Any]:
        """Queries the API parse details for a single page title."""
        params = {
            "action": "parse",
            "page": title,
            "prop": "text|sections|links|redirects",
            "format": "json",
            "redirects": "1"
        }
        
        data = self._query(params)
        if "error" in data:
            raise ValueError(data["error"].get("info", "Unknown API error"))
            
        return data.get("parse", {})
