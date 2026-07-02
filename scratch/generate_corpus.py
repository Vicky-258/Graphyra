import os
import json
from graphyra_adapter_genshin.adapter import GenshinWikiAdapter
from graphyra_adapter_genshin.exporter import JSONExporter


def generate():
    print("Initializing GenshinWikiAdapter for a seed crawl...")
    adapter = GenshinWikiAdapter()
    
    print("Crawling 500 pages from the Wiki (this can take a couple of minutes)...")
    res = adapter.ingest(max_pages=500)
    
    print(f"Crawl finished. Crawled {len(res.documents)} documents successfully.")
    
    exporter = JSONExporter()
    docs_dicts = [exporter.to_dict(doc) for doc in res.documents]
    
    output_path = os.path.join("data", "genshin_500_docs.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(docs_dicts, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved 500 documents to {output_path}!")


if __name__ == "__main__":
    generate()
