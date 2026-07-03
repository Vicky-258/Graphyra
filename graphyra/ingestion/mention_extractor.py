import re
from abc import ABC, abstractmethod
from typing import Set
from graphyra.models.chunk import Chunk


class MentionExtractor(ABC):

    @abstractmethod
    def extract_mentions(self, chunk: Chunk) -> Set[str]:
        """
        Analyzes a text chunk's content and extracts a set of candidate entity names/terms.
        """
        pass


class RegexMentionExtractor(MentionExtractor):

    def __init__(self, known_terms: Set[str]):
        self.known_terms = {t.strip() for t in known_terms if t.strip()}
        self._regex = None
        if self.known_terms:
            # Sort longest terms first to match greedily
            sorted_terms = sorted(list(self.known_terms), key=len, reverse=True)
            escaped = [re.escape(t) for t in sorted_terms]
            # Match boundary word tokens case-insensitively
            self._regex = re.compile(r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE)

    def extract_mentions(self, chunk: Chunk) -> Set[str]:
        if not self._regex or not chunk.content:
            return set()
        
        matches = self._regex.findall(chunk.content)
        extracted = set()
        
        # Map matches back to original case matching known terms
        for match in matches:
            for term in self.known_terms:
                if term.lower() == match.lower():
                    extracted.add(term)
                    break
        return extracted


class DictionaryMentionExtractor(MentionExtractor):
    """
    Dictionary-driven boundary-checking mention extractor.
    Enables robust matching of terms containing special characters (parentheses, slashes, quotes)
    by implementing custom character boundaries validation instead of standard regex '\b'.
    """

    def __init__(self, known_terms: Set[str]):
        self.set_known_terms(known_terms)

    def set_known_terms(self, known_terms: Set[str]):
        self.known_terms = {t.strip() for t in known_terms if t.strip()}
        self.sorted_terms = sorted(list(self.known_terms), key=len, reverse=True)

    def extract_mentions(self, chunk: Chunk) -> Set[str]:
        if not chunk.content:
            return set()
        
        content_lower = chunk.content.lower()
        extracted = set()
        matched_intervals = []
        
        for term in self.sorted_terms:
            term_lower = term.lower()
            term_len = len(term_lower)
            if term_len == 0:
                continue
            
            start_idx = 0
            while True:
                pos = content_lower.find(term_lower, start_idx)
                if pos == -1:
                    break
                
                end_idx = pos + term_len
                
                # Check for overlap with any previously matched interval (matches greedily from longest first)
                overlap = False
                for s, e in matched_intervals:
                    if not (end_idx <= s or pos >= e):
                        overlap = True
                        break
                
                if not overlap:
                    # Custom boundary check before position
                    valid_before = True
                    if pos > 0:
                        char_before = chunk.content[pos - 1]
                        if char_before.isalnum() or char_before == '_':
                            first_char_term = term[0]
                            if first_char_term.isalnum() or first_char_term == '_':
                                valid_before = False
                    
                    # Custom boundary check after end index
                    valid_after = True
                    if end_idx < len(chunk.content):
                        char_after = chunk.content[end_idx]
                        if char_after.isalnum() or char_after == '_':
                            last_char_term = term[-1]
                            if last_char_term.isalnum() or last_char_term == '_':
                                valid_after = False
                    
                    if valid_before and valid_after:
                        extracted.add(term)
                        matched_intervals.append((pos, end_idx))
                
                start_idx = pos + 1
        
        return extracted

