from html.parser import HTMLParser

class FandomParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_paragraph = False
        self.ignore_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")
        role = attrs_dict.get("role", "")
        
        is_ignored_class = any(
            ignored in class_name 
            for ignored in ["portable-infobox", "toc", "navbox", "thumb", "reference", "notice", "gallery"]
        )
        is_ignored_role = role in ["navigation", "region", "note"]
        
        if tag in ["script", "style", "aside", "table"] or is_ignored_class or is_ignored_role:
            self.ignore_depth += 1
        elif tag == "p" and self.ignore_depth == 0:
            self.in_paragraph = True

    def handle_endtag(self, tag):
        if tag in ["script", "style", "aside", "table"]:
            self.ignore_depth = max(0, self.ignore_depth - 1)
        elif tag == "p" and self.in_paragraph:
            self.in_paragraph = False
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.in_paragraph and self.ignore_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned + " ")

    def get_text(self):
        return "".join(self.text_parts).strip()

def main():
    # Mock output resembling the parse payload from genshin-impact.fandom.com
    html_content = """
    <div class="mw-content-ltr mw-parser-output" lang="en" dir="ltr">
        <aside role="region" class="portable-infobox pi-background pi-border-color">
            <h2>Nahida</h2>
            <div>Character details...</div>
        </aside>
        <p><b>Nahida</b> is a playable <a href="/wiki/Dendro" title="Dendro">Dendro</a> character in <i>Genshin Impact</i>.</p>
        <p>As Lesser Lord Kusanali and the Dendro Archon, she strives to have a stronger presence in <a href="/wiki/Sumeru" title="Sumeru">Sumeru</a> now that she has been freed from the <a href="/wiki/Sanctuary_of_Surasthana" title="Sanctuary of Surasthana">Sanctuary of Surasthana</a>.</p>
        <table class="toc">
            <tr><td>TOC Content</td></tr>
        </table>
        <p>She has deep connections to <a href="/wiki/Irminsul" title="Irminsul">Irminsul</a>.</p>
    </div>
    """
    
    links = [
        {"ns": 0, "*": "Dendro"},
        {"ns": 0, "*": "Sumeru"},
        {"ns": 0, "*": "Sanctuary of Surasthana"},
        {"ns": 0, "*": "Irminsul"},
        {"ns": 14, "*": "Category:Short Female Characters"}
    ]
    
    # Parse HTML
    parser = FandomParser()
    parser.feed(html_content)
    
    print("--- Extracted Clean Text ---")
    print(parser.get_text())
        
    print("\n--- Extracted Links (Namespace 0 only) ---")
    ns_links = [l["*"] for l in links if l.get("ns") == 0]
    print(ns_links)

if __name__ == "__main__":
    main()
