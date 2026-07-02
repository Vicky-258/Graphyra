import urllib.parse
from typing import Tuple, Dict, Any, List
from bs4 import BeautifulSoup, Tag
from graphyra.contracts import ContentBlock

class HTMLSanitizer:
    """
    Phase 1 HTML Sanitizer.
    Responsible for stripping boilerplate, extracting structured infoboxes,
    and compiling sanitization metrics before document parsing.
    """

    def __init__(self):
        # Selectors to decompose completely
        self.decomposed_selectors = [
            ".navbox",
            ".navbox-container",
            ".navbox-list",
            ".navbox-title",
            ".navbox-header",
            ".toc",
            "#toc",
            ".mw-editsection",
            "sup.reference",
            "ol.references",
            ".references",
            ".ambox",
            ".notice",
            ".spoiler",
            ".maintenance-img",
            ".mbox",
            "script",
            "style"
        ]

    def sanitize(self, html_content: str) -> Tuple[BeautifulSoup, List[ContentBlock], Dict[str, Any]]:
        """
        Cleans the HTML content.
        Returns:
            clean_soup: BeautifulSoup object containing the sanitized DOM.
            structured_blocks: List of ContentBlock objects extracted from Infoboxes.
            stats: Dictionary containing sanitization telemetry.
        """
        if not html_content:
            return BeautifulSoup("", "html.parser"), [], {}

        # 1. Parse initial DOM
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Target the main article body container
        content_div = soup.find(class_="mw-parser-output")
        if not content_div:
            # Fallback to full body if container is missing
            content_div = soup

        # 2. Capture metrics BEFORE cleaning
        # Parse links using standard '/wiki/' filter
        def count_links(element):
            a_tags = element.find_all("a")
            valid_links = [a for a in a_tags if a.get("href", "").startswith("/wiki/")]
            return len(valid_links)

        before_paragraphs = len(content_div.find_all("p"))
        before_tables = len(content_div.find_all("table"))
        before_links = count_links(content_div)
        before_size = len(str(content_div))

        # 3. Extract Infoboxes before decomposition
        structured_blocks: List[ContentBlock] = []
        infoboxes_removed = 0
        
        for infobox in content_div.find_all(class_="portable-infobox"):
            infobox_data = {}
            # Extract title if present
            title_el = infobox.find(class_="pi-title")
            if title_el:
                infobox_data["_title"] = title_el.text.strip()
            
            # Extract data labels and values
            for data_el in infobox.find_all(class_="pi-data"):
                label_el = data_el.find(class_="pi-data-label")
                value_el = data_el.find(class_="pi-data-value")
                if label_el and value_el:
                    label = label_el.text.strip().rstrip(":")
                    value = value_el.text.strip()
                    if label and value:
                        infobox_data[label] = value
            
            if infobox_data:
                # Store infobox as a domain-independent structured ContentBlock
                structured_blocks.append(ContentBlock(type="structured", content=infobox_data))
                infoboxes_removed += 1
            
            # Decompose the infobox so it doesn't get parsed as raw text
            infobox.decompose()

        # 4. Decompose unwanted tags
        elements_removed = {}
        for selector in self.decomposed_selectors:
            # Find and remove
            elements = content_div.select(selector)
            if elements:
                elements_removed[selector] = len(elements)
                for el in elements:
                    el.decompose()

        # Also decompose elements with classes like notice or ambox that might not be captured by direct selectors
        additional_notices = 0
        for tag in content_div.find_all(class_=lambda c: c and any(x in c for x in ["notice", "ambox", "spoiler-warning"])):
            try:
                tag.decompose()
                additional_notices += 1
            except Exception:
                pass
        if additional_notices:
            elements_removed["additional_notices"] = additional_notices

        # 5. Capture metrics AFTER cleaning
        after_paragraphs = len(content_div.find_all("p"))
        after_tables = len(content_div.find_all("table"))
        after_links = count_links(content_div)
        after_size = len(str(content_div))

        pct_removed = ((before_size - after_size) / before_size * 100) if before_size > 0 else 0

        stats = {
            "before": {
                "paragraphs": before_paragraphs,
                "tables": before_tables,
                "links": before_links,
                "size_bytes": before_size
            },
            "after": {
                "paragraphs": after_paragraphs,
                "tables": after_tables,
                "links": after_links,
                "size_bytes": after_size
            },
            "removed": {
                "elements_by_selector": elements_removed,
                "infoboxes_count": infoboxes_removed,
                "percentage_bytes": round(pct_removed, 2)
            }
        }

        return content_div, structured_blocks, stats
