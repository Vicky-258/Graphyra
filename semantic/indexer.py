from typing import List
from models.chunk import Chunk
from semantic.engine import EmbeddingEngine
from semantic.index import VectorIndex


class EmbeddingIndexer:
    """
    Coordinates semantic indexing lifecycle, supporting incremental indexing,
    full rebuilds, and auto-recovery on model drift.
    """

    def __init__(self, chunk_repo, embedding_engine: EmbeddingEngine, vector_index: VectorIndex):
        self.chunk_repo = chunk_repo
        self.embedding_engine = embedding_engine
        self.vector_index = vector_index

    def index_chunks(self, chunks: List[Chunk]) -> int:
        """
        Incrementally indexes a specific list of new or modified chunks.
        """
        self.vector_index.load_index()
        
        to_index = [c for c in chunks if c.id not in self.vector_index.ids]
        if not to_index:
            return 0

        texts = [c.content for c in to_index]
        batch_size = 64
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            embeddings.extend(self.embedding_engine.get_chunks_embeddings(batch))

        for chunk, vec in zip(to_index, embeddings):
            self.vector_index.add_vector(chunk.id, vec)
            
        self.vector_index.load_index()
        return len(to_index)

    def index_missing_chunks(self) -> int:
        """
        Fallback/rebuild scanning all chunks in the ChunkRepository.
        """
        all_chunks = self.chunk_repo.list_all()
        return self.index_chunks(all_chunks)

    def verify_and_rebuild_if_needed(self) -> bool:
        """
        Verifies model compatibility of the current vector index.
        If a mismatch is found, rebuilds the entire index.
        """
        model_name = getattr(self.embedding_engine.provider, "model_name", "mock_model")
        if not self.vector_index.verify_model(model_name):
            print(f"[EmbeddingIndexer] Model mismatch or uninitialized metadata detected. Invalidating and rebuild...")
            self.vector_index.clear()
            self.vector_index.load_index()
            self.index_missing_chunks()
            return True
        return False
