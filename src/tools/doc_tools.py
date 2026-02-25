from __future__ import annotations

import logging
import math
import re
from collections import Counter
from pathlib import Path

log = logging.getLogger(__name__)

_QUERIES = [
    "methodology and approach",
    "results and findings",
    "limitations and future work",
    "architecture and design decisions",
    "evaluation metrics",
]


def load_pdf(path: str | Path) -> list[str]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def chunk_text(pages: list[str], chunk_size: int = 512, overlap: int = 64) -> list[str]:
    text = "\n\n".join(pages)
    stride = chunk_size - overlap
    return [
        c for i in range(0, len(text), stride)
        if (c := text[i : i + chunk_size].strip())
    ]


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


def query_chunks(chunks: list[str], query: str, top_k: int = 5) -> list[str]:
    if not chunks:
        return []
    corpus = [_tokenize(c) for c in chunks]
    vecs = _tfidf(corpus)
    qvec = _tfidf([_tokenize(query)])[0]
    ranked = sorted(range(len(chunks)), key=lambda i: _cosine(qvec, vecs[i]), reverse=True)
    return [chunks[i] for i in ranked[:top_k]]


def ingest_pdf(path: str | Path, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    return chunk_text(load_pdf(path), chunk_size=chunk_size, overlap=overlap)


__all__ = ["load_pdf", "chunk_text", "query_chunks", "ingest_pdf"]
