import json
import sqlite3
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class SearchResult:
    id: str
    score: float


class VectorIndex(ABC):

    @abstractmethod
    def load_index(self) -> None:
        pass

    @abstractmethod
    def add_vector(self, id: str, vector: List[float]) -> None:
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int, threshold: float) -> List[SearchResult]:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def verify_model(self, model_name: str) -> bool:
        pass


class SQLiteVectorIndex(VectorIndex):
    """
    Default persistent implementation of VectorIndex.
    Uses a standalone SQLite database to store chunk embeddings.
    Checks model name alignment at startup to invalidate outdated indexes.
    """

    def __init__(self, db_path: str = "embeddings.db", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.model_name = model_name
        self.ids: List[str] = []
        self.vectors: Optional[np.ndarray] = None
        self._initialize_db()
        self.load_index()

    def _initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    vector TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def verify_model(self, model_name: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = 'model_name'")
            row = cursor.fetchone()
            if row is None:
                return False
            return row[0] == model_name
        finally:
            conn.close()

    def load_index(self) -> None:
        if not self.verify_model(self.model_name):
            self.clear()
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('model_name', ?)", (self.model_name,))
                conn.commit()
            finally:
                conn.close()

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, vector FROM vectors")
            rows = cursor.fetchall()
            
            self.ids = []
            vecs = []
            for r_id, r_vec in rows:
                self.ids.append(r_id)
                vecs.append(json.loads(r_vec))
                
            if vecs:
                self.vectors = np.array(vecs, dtype=np.float32)
                norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                self.vectors = self.vectors / norms
            else:
                self.vectors = None
        finally:
            conn.close()

    def add_vector(self, id: str, vector: List[float]) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            vector_str = json.dumps(vector)
            cursor.execute("INSERT OR REPLACE INTO vectors (id, vector) VALUES (?, ?)", (id, vector_str))
            conn.commit()
        finally:
            conn.close()

    def search(self, query_vector: List[float], top_k: int = 5, threshold: float = 0.0) -> List[SearchResult]:
        if self.vectors is None or len(self.vectors) == 0:
            return []
            
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm
            
        scores = np.dot(self.vectors, q_vec)
        
        results = []
        for idx, score in enumerate(scores):
            if score >= threshold:
                results.append(SearchResult(id=self.ids[idx], score=float(score)))
                
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vectors")
            cursor.execute("DELETE FROM metadata")
            conn.commit()
        finally:
            conn.close()
        self.ids = []
        self.vectors = None
