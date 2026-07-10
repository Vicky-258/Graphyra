from graphyra.ingestion.chunking import ChunkPolicy

DEFAULT_CHUNK_POLICY = ChunkPolicy(
    target_words=250,
    minimum_words=120,
    maximum_words=400,
    merge_short_paragraphs=True,
    preserve_tables=True,
    preserve_structured_blocks=True
)
