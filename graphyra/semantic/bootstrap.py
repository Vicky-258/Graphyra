import os
import traceback
from graphyra.storage.chunk_repository import ChunkRepository
from graphyra.semantic.config import SemanticConfig
from graphyra.semantic.providers import MockEmbeddingProvider, SentenceTransformerProvider
from graphyra.semantic.engine import EmbeddingEngine
from graphyra.semantic.index import SQLiteVectorIndex
from graphyra.semantic.fusion import CandidateFusionEngine
from graphyra.semantic.indexer import EmbeddingIndexer


def bootstrap_semantic_layer(storage, db_path: str = "embeddings.db") -> tuple:
    """
    Constructs and returns semantic components (embedding_engine, vector_index, fusion_engine, indexer)
    configured for Graphyra, fallback-safe for offline environments.
    """
    config = SemanticConfig()
    
    provider = None
    if config.provider == "sentence-transformers":
        try:
            provider = SentenceTransformerProvider(model_name=config.model)
            print(f"[Semantic Bootstrap] Loaded SentenceTransformer model: {config.model}")
        except Exception as e:
            print(f"[Semantic Bootstrap] Warning: Failed to load SentenceTransformer ({e}). Falling back to MockEmbeddingProvider.")
            
    if provider is None:
        provider = MockEmbeddingProvider(dimension=384)
        print("[Semantic Bootstrap] Initialized fallback MockEmbeddingProvider (dimension=384)")

    embedding_engine = EmbeddingEngine(provider)
    vector_index = SQLiteVectorIndex(db_path=db_path, model_name=config.model)
    chunk_repo = ChunkRepository(storage)
    indexer = EmbeddingIndexer(chunk_repo, embedding_engine, vector_index)
    fusion_engine = CandidateFusionEngine(
        direct_match_weight=config.direct_match_weight,
        semantic_match_weight=config.semantic_match_weight
    )

    return embedding_engine, vector_index, fusion_engine, indexer
