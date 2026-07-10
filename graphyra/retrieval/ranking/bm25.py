import math
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from graphyra.models.traversal_models import CandidateEvidence


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
    def __init__(self, k1: float = None, b: float = None, enable_stopwords: bool = None):
        from graphyra.config.ranking import DEFAULT_BM25_K1, DEFAULT_BM25_B, DEFAULT_BM25_ENABLE_STOPWORDS
        self.k1 = k1 if k1 is not None else DEFAULT_BM25_K1
        self.b = b if b is not None else DEFAULT_BM25_B
        self.enable_stopwords = enable_stopwords if enable_stopwords is not None else DEFAULT_BM25_ENABLE_STOPWORDS

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\w+", text.lower())
        if not self.enable_stopwords:
            return words
        stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
            "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont",
            "down", "during", "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have",
            "havent", "having", "he", "hed", "hell", "hes", "her", "here", "heres", "hers", "herself", "him",
            "himself", "his", "how", "hows", "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt",
            "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not",
            "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
            "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such",
            "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then", "there", "theres",
            "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to", "too",
            "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent",
            "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom",
            "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve",
            "your", "yours", "yourself", "yourselves"
        }
        return [w for w in words if w not in stopwords]

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
            
            # Repetition bias mitigation using structural properties
            if hasattr(candidate, "chunk") and candidate.chunk and candidate.chunk.metadata:
                features = candidate.chunk.metadata.get("features", {})
                if features:
                    rep_ratio = features.get("repeated_term_ratio", 0.0)
                    uniq_ratio = features.get("unique_term_ratio", 1.0)
                    if rep_ratio > 0.3 and uniq_ratio < 0.4:
                        # Apply a lexical penalty if repetition is high and unique vocabulary is low
                        penalty = max(0.1, (1.0 - rep_ratio) + uniq_ratio)
                        score_val *= penalty
            
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
