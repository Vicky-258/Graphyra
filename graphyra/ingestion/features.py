import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from graphyra.ingestion.chunking import split_into_sentences

@dataclass
class ChunkFeatures:
    token_count: int
    sentence_count: int
    average_sentence_length: float
    heading_depth: int
    list_ratio: float
    table_ratio: float
    key_value_ratio: float
    repeated_term_ratio: float
    unique_term_ratio: float
    entity_density: float
    link_density: float
    numeric_density: float
    punctuation_density: float
    block_depth: int

    def to_dict(self) -> dict:
        return {
            "token_count": self.token_count,
            "sentence_count": self.sentence_count,
            "average_sentence_length": self.average_sentence_length,
            "heading_depth": self.heading_depth,
            "list_ratio": self.list_ratio,
            "table_ratio": self.table_ratio,
            "key_value_ratio": self.key_value_ratio,
            "repeated_term_ratio": self.repeated_term_ratio,
            "unique_term_ratio": self.unique_term_ratio,
            "entity_density": self.entity_density,
            "link_density": self.link_density,
            "numeric_density": self.numeric_density,
            "punctuation_density": self.punctuation_density,
            "block_depth": self.block_depth
        }


class ChunkFeatureExtractor:
    """
    Computes generic structural and statistical features for a text chunk.
    Works entirely on observable properties, decoupled from domain semantics.
    """

    @staticmethod
    def extract_features(content: str, metadata: Optional[Dict[str, Any]] = None) -> ChunkFeatures:
        metadata = metadata or {}
        
        # 1. Word/Token metrics
        tokens = [t.lower() for t in re.findall(r'\b\w+\b', content)]
        token_count = len(tokens)
        
        # 2. Sentence metrics
        sentences = split_into_sentences(content)
        sentence_count = len(sentences)
        average_sentence_length = token_count / max(1, sentence_count)
        
        # 3. Line ratios (list, table, key-value)
        lines = content.splitlines()
        list_lines = sum(1 for l in lines if l.strip().startswith(('-', '*', '+')) or re.match(r'^\d+\.', l.strip()))
        list_ratio = list_lines / max(1, len(lines))
        
        table_lines = sum(1 for l in lines if l.count(':') > 1 and l.count(',') > 0)
        table_ratio = table_lines / max(1, len(lines))
        
        kv_lines = sum(1 for l in lines if ':' in l)
        key_value_ratio = kv_lines / max(1, len(lines))
        
        # 4. Lexical diversity and repetition
        word_counts = {}
        for t in tokens:
            word_counts[t] = word_counts.get(t, 0) + 1
        
        repeated_tokens = sum(count for w, count in word_counts.items() if count > 1)
        repeated_term_ratio = repeated_tokens / max(1, token_count)
        unique_term_ratio = len(word_counts) / max(1, token_count)
        
        # 5. Density metrics (entity and link density resolved in pipeline)
        entity_density = 0.0
        link_density = 0.0
        
        # 6. Character level densities
        num_chars = sum(1 for c in content if c.isdigit())
        numeric_density = num_chars / max(1, len(content))
        
        punc_chars = sum(1 for c in content if c in '.,;:!?()[]{}""\'\'`~@#$%^&*-+=_|\\/')
        punctuation_density = punc_chars / max(1, len(content))
        
        # 7. Hierarchy markers
        heading_depth = metadata.get("heading_depth", 0)
        block_depth = metadata.get("block_depth", 0)
        
        return ChunkFeatures(
            token_count=token_count,
            sentence_count=sentence_count,
            average_sentence_length=round(average_sentence_length, 2),
            heading_depth=heading_depth,
            list_ratio=round(list_ratio, 3),
            table_ratio=round(table_ratio, 3),
            key_value_ratio=round(key_value_ratio, 3),
            repeated_term_ratio=round(repeated_term_ratio, 3),
            unique_term_ratio=round(unique_term_ratio, 3),
            entity_density=entity_density,
            link_density=link_density,
            numeric_density=round(numeric_density, 3),
            punctuation_density=round(punctuation_density, 3),
            block_depth=block_depth
        )
