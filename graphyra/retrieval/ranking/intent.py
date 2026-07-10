import re
from dataclasses import dataclass

@dataclass
class QueryFeatures:
    query_length: int
    contains_numbers: bool
    contains_quotes: bool
    contains_boolean_words: bool
    contains_definition_pattern: bool
    contains_list_pattern: bool


class QueryFeaturesExtractor:
    """
    Extracts structural intent features from a natural language query.
    Operates purely on string properties and syntactic cues.
    """

    @staticmethod
    def extract_features(query: str) -> QueryFeatures:
        query_lower = query.lower().strip()
        words = query_lower.split()
        
        # 1. Length
        query_length = len(words)
        
        # 2. Contains numbers
        contains_numbers = any(char.isdigit() for char in query)
        
        # 3. Contains quotes
        contains_quotes = '"' in query or "'" in query
        
        # 4. Contains boolean indicators
        boolean_words = {"and", "or", "not", "union", "intersect"}
        contains_boolean_words = any(w in boolean_words for w in words)
        
        # 5. Definition / Explanation patterns
        definition_prefixes = [
            "who is", "what is", "where is", "who are", "what are",
            "explain", "describe", "tell me about", "history of",
            "background of", "origin of", "biography of"
        ]
        contains_definition_pattern = any(query_lower.startswith(p) for p in definition_prefixes) or (
            "who" in words or "what" in words or "where" in words or "explain" in words
        )
        
        # 6. List / Tabular patterns
        list_words = {
            "list", "members", "all", "every", "types", "categories",
            "translation", "localizations", "names", "stats", "attributes"
        }
        contains_list_pattern = any(w in list_words for w in words) or "list of" in query_lower
        
        return QueryFeatures(
            query_length=query_length,
            contains_numbers=contains_numbers,
            contains_quotes=contains_quotes,
            contains_boolean_words=contains_boolean_words,
            contains_definition_pattern=contains_definition_pattern,
            contains_list_pattern=contains_list_pattern
        )
