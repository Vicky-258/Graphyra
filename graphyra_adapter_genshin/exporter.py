import os
import json
from typing import Dict, Any, Optional
from graphyra.contracts import KnowledgeDocument


class JSONExporter:
    """
    Utility to export normalized KnowledgeDocuments into separate JSON files,
    one file per document, using the document title as the filename.
    """

    def __init__(self, default_output_dir: str = "output"):
        self.default_output_dir = default_output_dir

    def to_dict(self, doc: KnowledgeDocument) -> Dict[str, Any]:
        """Serializes a KnowledgeDocument dataclass structure into a serializable dictionary."""
        return {
            "id": doc.id,
            "title": doc.title,
            "source_type": doc.source_type,
            "metadata": doc.metadata,
            "sections": [
                {
                    "id": sec.id,
                    "title": sec.title,
                    "content_blocks": [
                        {"type": block.type, "content": block.content}
                        for block in sec.content_blocks
                    ]
                }
                for sec in doc.sections
            ],
            "references": [
                {
                    "source_document": ref.source_document,
                    "source_anchor": ref.source_anchor,
                    "target_document": ref.target_document,
                    "target_anchor": ref.target_anchor,
                    "reference_type": ref.reference_type
                }
                for ref in doc.references
            ]
        }

    def export(self, doc: KnowledgeDocument, output_dir: Optional[str] = None) -> str:
        """
        Writes a single KnowledgeDocument as a JSON file.
        Returns the absolute filepath to the exported file.
        """
        out_dir = output_dir or self.default_output_dir
        os.makedirs(out_dir, exist_ok=True)

        # Build clean filename from document title
        safe_title = doc.title.replace("/", "_").replace(":", "_").replace(" ", "_")
        filename = f"{safe_title}.json"
        filepath = os.path.join(out_dir, filename)

        doc_dict = self.to_dict(doc)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(doc_dict, f, indent=2, ensure_ascii=False)
            return os.path.abspath(filepath)
        except Exception as e:
            raise IOError(f"Failed to export document '{doc.title}' to '{filepath}': {e}")
