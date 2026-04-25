from __future__ import annotations

import hashlib
import math
import re
from typing import Dict, Iterable, List, Sequence

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "will",
    "with",
}


class HashEmbeddings:
    """Deterministic hashing embeddings with keyword expansion and token weighting.

    This keeps the project runnable offline while still simulating embedding behavior.
    """

    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        tokens = _tokenize(text)
        weighted_tokens = _weight_tokens(tokens)
        vec = [0.0] * self.dimension

        if not weighted_tokens:
            return vec

        for tok, weight in weighted_tokens.items():
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign * weight

        return _normalize(vec)

    def embed_batch(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must have same dimension")
    return sum(x * y for x, y in zip(a, b))


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def _tokenize(text: str) -> List[str]:
    base_tokens = [tok for tok in TOKEN_PATTERN.findall(text.lower()) if tok not in STOP_WORDS]
    base_tokens.extend(_expand_keywords(base_tokens))
    return base_tokens


def _weight_tokens(tokens: List[str]) -> Dict[str, float]:
    frequencies: Dict[str, float] = {}
    for tok in tokens:
        frequencies[tok] = frequencies.get(tok, 0.0) + 1.0

    # Dampen repetitive terms but preserve emphasis.
    for tok in list(frequencies.keys()):
        frequencies[tok] = math.sqrt(frequencies[tok])

    return frequencies


def _expand_keywords(tokens: List[str]) -> List[str]:
    extra: List[str] = []
    token_set = set(tokens)

    if {"openai", "model", "ai", "agent", "llm"} & token_set:
        extra.extend(["ai", "technology", "innovation", "software", "automation"])
    if {"crypto", "bitcoin", "blockchain", "defi"} & token_set:
        extra.extend(["crypto", "markets", "trading", "volatility"])
    if {"rates", "inflation", "market", "stocks", "equities", "fed"} & token_set:
        extra.extend(["finance", "market", "roi", "macro", "liquidity"])
    if {"privacy", "monopoly", "billionaire", "regulation"} & token_set:
        extra.extend(["skeptic", "society", "capitalism", "governance"])
    if {"ev", "battery", "electric", "vehicles"} & token_set:
        extra.extend(["energy", "technology", "infrastructure"])

    return extra
