from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

def load_pdf(path: str | Path) -> list[str]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]

def recursive_character_chunk(text: str, chunk_size: int, overlap: int, separators: list[str] = ["\n\n", "\n", " ", ""]) -> list[str]:
    """Sophisticated recursive chunking to maintain semantic context."""
    if len(text) <= chunk_size:
        return [text]
    
    # Try the first separator
    sep = separators[0]
    final_chunks = []
    
    if sep:
        splits = text.split(sep)
    else:
        splits = list(text)
        
    current_chunk = ""
    for s in splits:
        if current_chunk and len(current_chunk) + len(s) + len(sep) > chunk_size:
            final_chunks.append(current_chunk.strip())
            # Maintain overlap
            # Simplified: take last 'overlap' chars
            current_chunk = current_chunk[-overlap:] + sep + s
        else:
            if current_chunk:
                current_chunk += sep + s
            else:
                current_chunk = s
                
    if current_chunk:
        # If a single split is still too large, recurse with next separator
        if len(current_chunk) > chunk_size and len(separators) > 1:
            final_chunks.extend(recursive_character_chunk(current_chunk, chunk_size, overlap, separators[1:]))
        else:
            final_chunks.append(current_chunk.strip())
            
    return [c for c in final_chunks if c]

def chunk_text(pages: list[str], chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Sophisticated chunking entry point."""
    all_text = "\n\n".join(pages)
    return recursive_character_chunk(all_text, chunk_size, overlap)

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

def _tfidf(corpus: list[list[str]]) -> list[dict[str, float]]:
    n = len(corpus)
    tfs = [Counter(doc) for doc in corpus]
    vocab = set(t for tf in tfs for t in tf)
    idf = {t: math.log((1 + n) / (1 + sum(1 for tf in tfs if t in tf))) + 1 for t in vocab}
    return [{t: c * idf[t] for t, c in tf.items()} for tf in tfs]

def _cosine(a: dict, b: dict) -> float:
    dot = sum(a.get(t, 0) * v for t, v in b.items())
    return dot / ((math.sqrt(sum(v**2 for v in a.values())) or 1e-9) *
                  (math.sqrt(sum(v**2 for v in b.values())) or 1e-9))

def get_pdf_metadata(path: str | Path) -> dict[str, Any]:
    """Extract standard PDF metadata fields."""
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    meta = reader.metadata
    if not meta:
        return {}
    return {
        "author": meta.author,
        "creator": meta.creator,
        "producer": meta.producer,
        "subject": meta.subject,
        "title": meta.title,
        "pages": len(reader.pages)
    }

def query_chunks(chunks: list[str], query: str, top_k: int = 5, min_score: float = 0.1) -> list[str]:
    """Retrieves top_k chunks, filtering out those below min_score similarity."""
    if not chunks:
        return []
    corpus = [_tokenize(c) for c in chunks]
    vecs = _tfidf(corpus)
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    qvec = _tfidf([q_tokens])[0]
    
    # Calculate scores and sort
    scored_indices = []
    for i, vec in enumerate(vecs):
        score = _cosine(qvec, vec)
        if score >= min_score:
            scored_indices.append((i, score))
            
    scored_indices.sort(key=lambda x: x[1], reverse=True)
    return [chunks[i] for i, _ in scored_indices[:top_k]]

def extract_file_paths(text: str) -> list[str]:
    """Extracts suspected file paths from text using patterns."""
    pattern = r'(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]{2,4}'
    p = re.compile(pattern)
    paths = p.findall(text)
    return sorted(list(set(paths)))

def verify_theoretical_depth(chunks: list[str]) -> dict:
    """Checks for rubric keywords and substantive explanations."""
    keywords = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"]
    results = {}
    for kw in keywords:
        matches = query_chunks(chunks, kw, top_k=3, min_score=0.2)
        results[kw] = {
            "found": len(matches) > 0,
            "substantive": any(len(m) > 100 for m in matches),
            "snippets": matches[:1]
        }
    return results

def ingest_pdf(path: str | Path, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    return chunk_text(load_pdf(path), chunk_size=chunk_size, overlap=overlap)

__all__ = ["load_pdf", "chunk_text", "query_chunks", "ingest_pdf", "get_pdf_metadata", "extract_file_paths", "verify_theoretical_depth"]
