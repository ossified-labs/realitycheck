"""Pure-Python text utilities: passage splitting, lexical relevance, near-duplicate detection,
quote verification and prompt-injection heuristics. No external dependencies, so it is easy
to test and to swap for embeddings (sentence-transformers) later."""
from __future__ import annotations

import math
import re
from collections import Counter

STOPWORDS = set("""
a an the and or but if of to in on for with by from at as is are was were be been being this that
these those it its into than then so such not no do does did can could may might will would should
has have had about over under more most less least very also which who whom what when where why how
""".split())

_WORD = re.compile(r"[a-z0-9]+")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def tokens(text: str) -> list[str]:
    return [t for t in _WORD.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def split_passages(text: str, sentences_per_passage: int = 4, max_passages: int = 200) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sents = [s for s in _SENT.split(text) if len(s) > 20]
    if not sents:
        return [text[:1500]]
    step = max(1, sentences_per_passage - 1)  # 1-sentence overlap between windows
    out = []
    for i in range(0, len(sents), step):
        out.append(" ".join(sents[i:i + sentences_per_passage])[:1500])
        if len(out) >= max_passages:
            break
    return out


def bm25_rank(query: str, passages: list[str], k1: float = 1.5, b: float = 0.75) -> list[tuple[int, float]]:
    """Return (passage_index, score) sorted best first."""
    q = tokens(query)
    docs = [tokens(p) for p in passages]
    if not docs or not q:
        return [(i, 0.0) for i in range(len(passages))]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n or 1.0
    df = Counter(t for d in docs for t in set(d))
    scores = []
    for i, d in enumerate(docs):
        tf = Counter(d)
        s = 0.0
        for t in q:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append((i, s))
    return sorted(scores, key=lambda x: x[1], reverse=True)


def coverage(query: str, passage: str) -> float:
    """Share of query terms present in the passage, 0..1. Used as a bounded relevance score."""
    q = set(tokens(query))
    if not q:
        return 0.0
    return len(q & set(tokens(passage))) / len(q)


def shingles(text: str, k: int = 5) -> set[tuple[str, ...]]:
    t = tokens(text)
    return {tuple(t[i:i + k]) for i in range(max(0, len(t) - k + 1))}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def normalize_for_match(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9%.' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_in_passage(quote: str, passage: str) -> bool:
    """True only if the quote actually appears in the retrieved passage (whitespace/punctuation-tolerant)."""
    q = normalize_for_match(quote)
    if len(q) < 12:
        return False
    return q in normalize_for_match(passage)


INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above)",
    r"you are (now )?(an? )?(ai|assistant|language model|chatgpt|claude)",
    r"system prompt",
    r"(new|updated) instructions?:",
    r"respond (only )?with ['\"]?(true|supported|verified)",
    r"(label|classify|mark) (this|the claim) as (true|supported|supporting)",
    r"</?(system|assistant|instructions?)>",
]
_INJ = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    return bool(_INJ.search(text or ""))


def sanitize_untrusted(text: str) -> str:
    """Neutralise tag-like markup so retrieved text cannot close our <source> wrapper."""
    return text.replace("<", "‹").replace(">", "›")
