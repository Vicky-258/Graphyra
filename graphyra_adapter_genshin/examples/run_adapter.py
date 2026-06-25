#!/usr/bin/env python3
import os
import sys
import argparse
from unittest.mock import patch

# Ensure correct PYTHONPATH resolving graphyra contracts & current adapter package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../tests/mocks")))

from graphyra_adapter_genshin import GenshinWikiAdapter, GenshinWikiParser
from graphyra_adapter_genshin.exporter import JSONExporter
from graphyra_adapter_genshin.mediawiki_client import MediaWikiClient


def main():
    parser = argparse.ArgumentParser(
        description="Demo/run script for the Graphyra Genshin Wiki adapter."
    )
    parser.add_argument(
        "--mode",
        choices=["offline-parse", "mock-crawl", "live-crawl"],
        default="offline-parse",
        help="Crawl mode: offline-parse (default), mock-crawl (offline simulation), or live-crawl (requires internet)",
    )
    parser.add_argument(
        "--output-dir",
        default="example_output",
        help="Directory to save exported JSON files",
    )
    args = parser.parse_args()

    # Create exporter
    exporter = JSONExporter(default_output_dir=args.output_dir)

    if args.mode == "offline-parse":
        print("=== Mode: Offline HTML Parsing ===")
        # Load local mock HTML fixture
        fixture_path = os.path.join(
            os.path.dirname(__file__), "../tests/fixtures/nahida_mock.html"
        )
        if not os.path.exists(fixture_path):
            print(f"Error: Fixture HTML not found at {fixture_path}")
            sys.exit(1)

        with open(fixture_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Instantiate pure parser
        wiki_parser = GenshinWikiParser(source_id_prefix="genshin_fandom:main")
        print("Parsing offline HTML for Nahida...")
        documents = wiki_parser.parse(html_content, "Nahida")

        for doc in documents:
            print(f"\nSuccessfully Parsed Document: {doc.title} (ID: {doc.id})")
            print(f"Sections discovered: {[s.title for s in doc.sections]}")
            print(f"References discovered: {len(doc.references)}")

            # Export to file
            out_file = exporter.export(doc)
            print(f"Saved exported document to: {out_file}")

    elif args.mode == "mock-crawl":
        print("=== Mode: Mock Offline Ingestion Crawl ===")
        # Setup mocking for MediaWikiClient requests to simulate network offline behavior
        with patch.object(
            MediaWikiClient, "discover_all_page_titles"
        ) as mock_discover_titles, patch.object(
            MediaWikiClient, "get_page_revisions"
        ) as mock_get_revisions, patch.object(
            MediaWikiClient, "fetch_page_parse"
        ) as mock_fetch_parse:

            mock_discover_titles.return_value = ["Nahida", "Irminsul"]
            mock_get_revisions.return_value = {
                "Nahida": {"revid": 200, "timestamp": "2026-06-25T00:00:00Z"},
                "Irminsul": {"revid": 300, "timestamp": "2026-06-25T00:00:00Z"},
            }
            mock_fetch_parse.side_effect = [
                {
                    "title": "Irminsul",
                    "text": {
                        "*": "<div class='mw-parser-output'><p>Irminsul is the world tree.</p></div>"
                    },
                },
                {
                    "title": "Nahida",
                    "text": {
                        "*": "<div class='mw-parser-output'><p>Nahida resides in Sumeru.</p></div>"
                    },
                },
            ]

            # Run adapter ingestion
            adapter = GenshinWikiAdapter(
                endpoint_url="https://mock-api.local/api.php",
                source_id_prefix="genshin_fandom:main",
                cache_file_path="example_crawl_cache.json",
                output_dir=args.output_dir,
            )

            print("Initiating adapter mock ingest() crawl...")
            result = adapter.ingest()

            print("\n--- Crawl Telemetry Summary ---")
            print(f"Discovered: {result.pages_discovered}")
            print(f"Processed:  {result.pages_processed}")
            print(f"New:        {result.pages_new}")
            print(f"Updated:    {result.pages_updated}")
            print(f"Deleted:    {result.pages_deleted}")
            print(f"Failures:   {result.failed_pages}")

            # Export output documents
            for doc in result.documents:
                out_path = exporter.export(doc)
                print(f"Saved: {out_path}")

            # Cleanup example cache
            if os.path.exists("example_crawl_cache.json"):
                os.remove("example_crawl_cache.json")

    elif args.mode == "live-crawl":
        print("=== Mode: Live Ingestion Crawl ===")
        print("Warning: This requires internet access and Fandom API connectivity.")
        
        adapter = GenshinWikiAdapter(
            endpoint_url="https://genshin-impact.fandom.com/api.php",
            source_id_prefix="genshin_fandom:main",
            cache_file_path="example_live_crawl_cache.json",
            output_dir=args.output_dir,
        )

        try:
            print("Fetching live content from Fandom Wiki...")
            result = adapter.ingest_pages(["Nahida", "Irminsul"])

            print("\n--- Live Ingestion Crawl Telemetry ---")
            print(f"Discovered: {result.pages_discovered}")
            print(f"Processed:  {result.pages_processed}")
            print(f"Failures:   {result.failed_pages}")

            # Export files
            for doc in result.documents:
                out_path = exporter.export(doc)
                print(f"Saved: {out_path}")

        except Exception as e:
            print(f"\nLive crawl failed: {e}")
            print("Please check internet settings or run with --mode offline-parse / --mode mock-crawl.")

        # Cleanup cache
        if os.path.exists("example_live_crawl_cache.json"):
            os.remove("example_live_crawl_cache.json")


if __name__ == "__main__":
    main()
