import math
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from models.traversal_models import CandidateEvidence


class LexicalIndex(ABC):
    """
    Abstract interface for lexical evidence lookup and relevance scoring.
    Isolate the ranking pipeline from specific indexing engines (SQLite FTS, Lucene, etc.).
    """
    @abstractmethod
    def score(self, query: str, candidates: List[CandidateEvidence]) -> List[CandidateEvidence]:
        pass


class BM25LexicalIndex(LexicalIndex):
    """
    Default in-memory implementation of LexicalIndex using Okapi BM25.
    Evaluates term match relevance over the provided CandidateEvidence pool.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def score(self, query: str, candidates: List[CandidateEvidence]) -> List[CandidateEvidence]:
        if not candidates:
            return candidates

        query_tokens = self._tokenize(query)
        if not query_tokens:
            for c in candidates:
                c.bm25_score = 0.0
            return candidates

        N = len(candidates)
        doc_lengths = []
        doc_term_freqs = []  # List[Dict[str, int]]
        doc_contains_term: Dict[str, int] = {}

        for candidate in candidates:
            tokens = self._tokenize(candidate.content)
            doc_lengths.append(len(tokens))
            
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            doc_term_freqs.append(tf)

            for t in tf.keys():
                doc_contains_term[t] = doc_contains_term.get(t, 0) + 1

        avgdl = sum(doc_lengths) / N if N > 0 else 0.0

        # Calculate IDF for query terms
        idf = {}
        for t in query_tokens:
            n_q = doc_contains_term.get(t, 0)
            # Okapi BM25 IDF formulation
            idf_val = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
            idf[t] = max(0.0, idf_val)

        # Apply BM25 score to each candidate
        for idx, candidate in enumerate(candidates):
            score_val = 0.0
            tf = doc_term_freqs[idx]
            dl = doc_lengths[idx]

            for t in query_tokens:
                f_q = tf.get(t, 0)
                if f_q > 0:
                    denominator = f_q + self.k1 * (1.0 - self.b + self.b * (dl / avgdl if avgdl > 0 else 1.0))
                    score_val += idf[t] * (f_q * (self.k1 + 1.0)) / denominator
            
            candidate.bm25_score = score_val

        return candidates


class BM25Scorer:
    """
    Signal orchestrator that consumes a LexicalIndex provider to enrich candidates.
    """
    def __init__(self, index: Optional[LexicalIndex] = None):
        self.index = index or BM25LexicalIndex()

    def score(self, query: str, candidates: List[CandidateEvidence]) -> List[CandidateEvidence]:
        # Delegate lexical scoring to index provider
        return self.index.score(query, candidates)
