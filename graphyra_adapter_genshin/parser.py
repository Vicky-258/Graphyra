import urllib.parse
from typing import List, Dict, Any, Set
from bs4 import BeautifulSoup, Tag

from graphyra.contracts import (
    KnowledgeDocument,
    Section,
    Reference,
    ContentBlock
)


class GenshinWikiParser:
    """
    Core normalization parser.
    Transforms raw HTML strings into Graphyra KnowledgeDocuments.
    Works in complete isolation without network or cache dependencies.
    """

    def __init__(self, source_id_prefix: str = "genshin_fandom:main"):
        self.source_id_prefix = source_id_prefix

    def parse(self, html_content: str, title: str) -> List[KnowledgeDocument]:
        """
        Parses raw HTML text, returning a list of extracted KnowledgeDocuments.
        (Usually returns one main page document, but can return multiple in case of inline redirects).
        """
        if not html_content:
            return []

        doc_id = f"{self.source_id_prefix}:{title.replace(' ', '_')}"
        doc = KnowledgeDocument(
            id=doc_id,
            title=title,
            source_type="mediawiki"
        )

        soup = BeautifulSoup(html_content, "html.parser")
        
        # In Fandom page renderings, content lives under the .mw-parser-output container
        content_div = soup.find(class_="mw-parser-output") or soup

        # 1. Establish the default Introduction section
        current_section = Section(id="Introduction", title="Introduction")
        doc.sections.append(current_section)

        # Non-knowledge layout classes to discard
        ignored_classes = ["toc", "navbox", "portable-infobox", "gallery", "notice", "reference", "thumb"]

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

        # Parse block elements
        for child in content_div.children:
            if not isinstance(child, Tag):
                continue

            # Bypass ignored components
            classes = child.get("class", [])
            if any(cls in ignored_classes for cls in classes):
                continue
            if child.name in ["aside", "style", "script"]:
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
                # Strip helper citations like [1]
                for sup in child.find_all("sup", class_="reference"):
                    sup.decompose()
                
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
                    for sup in li.find_all("sup", class_="reference"):
                        sup.decompose()
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
