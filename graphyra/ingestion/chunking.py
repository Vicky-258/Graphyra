import re
from typing import List
from dataclasses import dataclass
from graphyra.interfaces.models import Section

@dataclass
class ChunkPolicy:
    target_words: int = 250
    minimum_words: int = 120
    maximum_words: int = 400
    merge_short_paragraphs: bool = True
    preserve_tables: bool = True
    preserve_structured_blocks: bool = True


def split_into_sentences(text: str) -> List[str]:
    """
    Splits text by sentence boundaries, ignoring common abbreviations,
    numbered lists, and quotes to prevent noise fragments.
    """
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = []
    buffer = ""
    abbrev_patterns = re.compile(
        r'\b(e\.g|i\.e|mr|mrs|dr|vs|al|approx|ca|vol|no|ref|chk|ent|art|gen|fandom|main|pt|p)\.$',
        re.IGNORECASE
    )
    number_pattern = re.compile(r'\b\d+\.$')
    
    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        if buffer:
            buffer += " " + s
        else:
            buffer = s
        
        # Keep buffering if sentence ends in abbreviation or trailing list number
        if abbrev_patterns.search(buffer) or number_pattern.search(buffer) or (buffer.endswith('"') and len(buffer) < 4):
            continue
        
        sentences.append(buffer)
        buffer = ""
    if buffer:
        sentences.append(buffer)
    return sentences


class ParagraphChunker:
    """
    Paragraph-First chunking strategy.
    Groups content blocks at the paragraph level, preserving semantic author intent.
    Falls back to sentence splitting only as a last resort for oversized paragraphs.
    """

    def __init__(self, policy: ChunkPolicy = None):
        self.policy = policy or ChunkPolicy()

    def chunk_document(self, sections: List[Section]) -> List[dict]:
        chunks = []
        
        for section in sections:
            current_text_blocks = []
            current_word_count = 0
            
            def emit_text_chunk():
                nonlocal current_text_blocks, current_word_count
                if not current_text_blocks:
                    return
                content_str = "\n\n".join(current_text_blocks)
                chunks.append({
                    "content": content_str,
                    "section_id": section.id
                })
                current_text_blocks = []
                current_word_count = 0

            for block in section.content_blocks:
                if block.type == "text":
                    content = (block.content or "").strip()
                    if not content:
                        continue
                    
                    block_words = len(content.split())
                    
                    # Merge logic based on paragraph boundaries
                    if current_word_count + block_words <= self.policy.target_words:
                        current_text_blocks.append(content)
                        current_word_count += block_words
                    elif self.policy.merge_short_paragraphs and current_word_count + block_words <= self.policy.maximum_words:
                        current_text_blocks.append(content)
                        current_word_count += block_words
                        emit_text_chunk()
                    else:
                        # Exceeds targets. Flush existing buffer
                        if current_word_count >= self.policy.minimum_words:
                            emit_text_chunk()
                        
                        # Add new block if fits as a standalone chunk
                        if block_words <= self.policy.maximum_words:
                            if current_text_blocks:
                                emit_text_chunk()
                            current_text_blocks.append(content)
                            current_word_count = block_words
                        else:
                            # Last resort: split the oversized paragraph into sentences
                            if current_text_blocks:
                                emit_text_chunk()
                            
                            sentences = split_into_sentences(content)
                            for sent in sentences:
                                sent_words = len(sent.split())
                                if current_word_count + sent_words <= self.policy.target_words:
                                    current_text_blocks.append(sent)
                                    current_word_count += sent_words
                                elif current_word_count + sent_words <= self.policy.maximum_words:
                                    current_text_blocks.append(sent)
                                    current_word_count += sent_words
                                    emit_text_chunk()
                                else:
                                    if current_text_blocks:
                                        emit_text_chunk()
                                    current_text_blocks.append(sent)
                                    current_word_count = sent_words
                                    
                elif block.type == "structured":
                    emit_text_chunk()
                    data = block.content or {}
                    
                    if self.policy.preserve_structured_blocks:
                        current_batch = []
                        current_batch_words = 0
                        for k, v in data.items():
                            if k.startswith("_"):
                                continue
                            record_str = f"{k}: {v}"
                            record_words = len(record_str.split())
                            
                            if current_batch_words + record_words > self.policy.target_words:
                                if current_batch:
                                    chunks.append({
                                        "content": "\n".join(current_batch),
                                        "section_id": section.id
                                    })
                                current_batch = [record_str]
                                current_batch_words = record_words
                            else:
                                current_batch.append(record_str)
                                current_batch_words += record_words
                        if current_batch:
                            chunks.append({
                                "content": "\n".join(current_batch),
                                "section_id": section.id
                            })
                    else:
                        statements = [f"{k}: {v}" for k, v in data.items() if not k.startswith("_")]
                        if statements:
                            chunks.append({
                                "content": ". ".join(statements) + ".",
                                "section_id": section.id
                            })

                elif block.type == "table":
                    emit_text_chunk()
                    headers = block.content.get("headers", [])
                    rows = block.content.get("rows", [])
                    
                    if self.policy.preserve_tables:
                        current_batch = []
                        current_batch_words = 0
                        for row in rows:
                            row_vals = [f"{h}: {val}" for h, val in zip(headers, row) if val]
                            if not row_vals:
                                continue
                            row_str = ", ".join(row_vals)
                            row_words = len(row_str.split())
                            
                            if current_batch_words + row_words > self.policy.target_words:
                                if current_batch:
                                    chunks.append({
                                        "content": "\n".join(current_batch),
                                        "section_id": section.id
                                    })
                                current_batch = [row_str]
                                current_batch_words = row_words
                            else:
                                current_batch.append(row_str)
                                current_batch_words += row_words
                        if current_batch:
                            chunks.append({
                                "content": "\n".join(current_batch),
                                "section_id": section.id
                            })
                    else:
                        statements = []
                        for row in rows:
                            row_vals = [f"{h}: {val}" for h, val in zip(headers, row) if val]
                            if row_vals:
                                statements.append(", ".join(row_vals))
                        if statements:
                            chunks.append({
                                "content": ". ".join(statements) + ".",
                                "section_id": section.id
                            })

            # Emit any remaining text buffer at end of section
            emit_text_chunk()

        return chunks
