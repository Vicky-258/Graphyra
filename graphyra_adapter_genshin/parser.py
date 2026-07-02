import urllib.parse
from typing import List, Dict, Any, Set, Optional
from bs4 import BeautifulSoup, Tag

from graphyra.contracts import (
    KnowledgeDocument,
    Section,
    Reference,
    ContentBlock
)
from graphyra_adapter_genshin.sanitizer import HTMLSanitizer


class GenshinWikiParser:
    """
    Core normalization parser.
    Transforms raw HTML strings into Graphyra KnowledgeDocuments.
    Works in complete isolation without network or cache dependencies.
    """

    def __init__(self, source_id_prefix: str = "genshin_fandom:main"):
        self.source_id_prefix = source_id_prefix
        self.last_sanitization_stats: Dict[str, Any] = {}

    def parse(self, html_content: str, title: str, redirects: Optional[List[Dict[str, Any]]] = None) -> List[KnowledgeDocument]:
        """
        Parses raw HTML text, returning a list of extracted KnowledgeDocuments.
        """
        if not html_content:
            return []

        doc_id = f"{self.source_id_prefix}:{title.replace(' ', '_')}"
        doc = KnowledgeDocument(
            id=doc_id,
            title=title,
            source_type="mediawiki"
        )

        # 1. Run HTML Sanitization Stage (boilerplate cleanup, infobox structured extraction)
        sanitizer = HTMLSanitizer()
        content_div, structured_blocks, stats = sanitizer.sanitize(html_content)
        self.last_sanitization_stats = stats

        # 2. Establish the default Introduction section and append structured infobox content blocks
        current_section = Section(id="Introduction", title="Introduction")
        current_section.content_blocks.extend(structured_blocks)
        doc.sections.append(current_section)

        # Process redirects list into Reference components
        if redirects:
            for r in redirects:
                from_title = r.get("from", "")
                to_title = r.get("to", "")
                if from_title and to_title:
                    ref = Reference(
                        source_document=f"{self.source_id_prefix}:{from_title.replace(' ', '_')}",
                        source_anchor="",
                        target_document=f"{self.source_id_prefix}:{to_title.replace(' ', '_')}",
                        target_anchor="",
                        reference_type="redirects_to"
                    )
                    doc.references.append(ref)

        # Track unique references
        seen_refs: Set[tuple] = set()

        def parse_links(element: Tag, current_sec_id: str):
            """Parses and formats inline links inside standard tag content."""
            for link in element.find_all("a"):
                href = link.get("href", "")
                if not href.startswith("/wiki/"):
                    continue

                # Remove query string variables if present
                href_path = href.split("?")[0]
                
                # Split target page title from section anchor hash
                parts = href_path[len("/wiki/"):].split("#")
                target_name = parts[0]
                target_anchor = parts[1] if len(parts) > 1 else ""

                # Skip special MediaWiki utility namespaces
                ignored_namespaces = ["Template:", "Talk:", "User:", "Forum:", "Module:", "File:", "Special:", "MediaWiki:"]
                if any(target_name.startswith(ns) for ns in ignored_namespaces):
                    continue

                # Generate targets depending on hyperlink vs category classifications
                if target_name.startswith("Category:"):
                    category_title = target_name[len("Category:"):]
                    source_parts = self.source_id_prefix.split(":")
                    source_name = source_parts[0] if source_parts else "source"
                    target_doc_id = f"{source_name}:category:{category_title}"
                    ref_type = "category"
                else:
                    target_doc_id = f"{self.source_id_prefix}:{target_name}"
                    ref_type = "hyperlink"

                ref = Reference(
                    source_document=doc.id,
                    source_anchor=current_sec_id,
                    target_document=urllib.parse.unquote(target_doc_id),
                    target_anchor=urllib.parse.unquote(target_anchor),
                    reference_type=ref_type
                )
                
                ref_key = (ref.source_document, ref.source_anchor, ref.target_document, ref.target_anchor, ref.reference_type)
                if ref_key not in seen_refs:
                    seen_refs.add(ref_key)
                    doc.references.append(ref)

        def is_nested_in_list_or_table(tag: Tag) -> bool:
            """Helper to check if a block element resides inside a list or a table."""
            parent = tag.parent
            while parent and parent != content_div:
                if parent.name in ["ul", "ol", "li", "table", "tr", "td", "th"]:
                    return True
                parent = parent.parent
            return False

        # 3. Parse block elements recursively (enables nesting support like tabbers/columns)
        for child in content_div.find_all(["h2", "h3", "p", "ul", "ol", "table", "pre"], recursive=True):
            # Skip elements nested inside tables or lists to prevent double extraction
            if is_nested_in_list_or_table(child):
                continue

            # Bypass ignored elements like image galleries/thumbs
            classes = child.get("class", [])
            if any(cls in ["gallery", "thumb"] for cls in classes):
                continue

            # A. Heading Splitters (h2, h3)
            if child.name in ["h2", "h3"]:
                headline_span = child.find("span", class_="mw-headline")
                if headline_span:
                    sec_id = headline_span.get("id", "").strip()
                    sec_title = headline_span.text.strip()
                    if not sec_id:
                        sec_id = sec_title.replace(" ", "_")
                        
                    current_section = Section(id=sec_id, title=sec_title)
                    doc.sections.append(current_section)
                continue

            # B. Standard Paragraph Block
            if child.name == "p":
                p_text = child.text.strip()
                if p_text:
                    block = ContentBlock(type="text", content=p_text)
                    current_section.content_blocks.append(block)
                    parse_links(child, current_section.id)
                continue

            # C. Lists Compilation
            if child.name in ["ul", "ol"]:
                items = []
                for li in child.find_all("li", recursive=False):
                    li_text = li.text.strip()
                    if li_text:
                        items.append(li_text)
                        parse_links(li, current_section.id)
                
                if items:
                    list_text = "\n".join(f"- {itm}" for itm in items)
                    block = ContentBlock(type="text", content=list_text)
                    current_section.content_blocks.append(block)
                continue

            # D. Table Compilation
            if child.name == "table":
                headers = [th.text.strip() for th in child.find_all("th")]
                rows = []
                for tr in child.find_all("tr"):
                    tds = tr.find_all("td")
                    if tds:
                        row_cells = [td.text.strip() for td in tds]
                        rows.append(row_cells)
                        parse_links(tr, current_section.id)
                
                if headers or rows:
                    table_dict = {
                        "headers": headers,
                        "rows": rows
                    }
                    block = ContentBlock(type="table", content=table_dict)
                    current_section.content_blocks.append(block)
                continue

            # E. Code snippets
            if child.name == "pre":
                block = ContentBlock(type="code", content=child.text.strip())
                current_section.content_blocks.append(block)
                continue

        return [doc]
