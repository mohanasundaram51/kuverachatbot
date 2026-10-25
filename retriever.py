"""Keyword search (BM25) over data/corpus.json, filtered by scheme."""

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

CORPUS_PATH = Path(__file__).parent / "data" / "corpus.json"

# scheme key (used in code) -> value in the sources.csv "scheme" column
SCHEME_LABELS = {"large_cap": "Large Cap", "small_cap": "Small Cap", "elss": "ELSS"}
SHARED_LABELS = {"General", "All"}  # always searched, whatever the scheme

# question topic -> doc types that hold that fact best
BOOSTS = [
    (r"exit load|minimum|\bsip\b|lock.?in", {"KIM", "Scheme page"}),
    (r"expense ratio|\bter\b|benchmark|risk.?o.?meter", {"Fund Facts"}),
]
BOOST_FACTOR = 1.5

# question wording -> words the official documents use for the same thing
SYNONYMS = [
    (r"minimum.{0,20}(sip|investment|amount)|(sip|investment).{0,20}minimum", "application amount purchase"),
]

STOPWORDS = {
    "a", "an", "the", "of", "for", "is", "are", "what", "how", "do", "does", "i",
    "my", "me", "to", "in", "on", "and", "or", "it", "its", "this", "that", "have",
    "has", "be", "can", "with", "from", "by", "at", "hdfc", "fund", "scheme",
}


def tokenize(text):
    text = text.lower().replace("lockin", "lock in")
    words = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?%?", text)
    return [w for w in words if w not in STOPWORDS]


CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
CHUNKS_BY_ID = {c["chunk_id"]: c for c in CORPUS}
_BM25 = BM25Okapi([tokenize(c["text"]) for c in CORPUS])


def search(question, scheme, k=5):
    """Return the top k chunks for the question.

    scheme is "large_cap", "small_cap", "elss" or "general".
    """
    allowed = set(SHARED_LABELS)
    if scheme in SCHEME_LABELS:
        allowed.add(SCHEME_LABELS[scheme])

    preferred = set()
    for pattern, doc_types in BOOSTS:
        if re.search(pattern, question, re.I):
            preferred |= doc_types

    query = question
    for pattern, extra_words in SYNONYMS:
        if re.search(pattern, question, re.I):
            query += " " + extra_words

    scores = _BM25.get_scores(tokenize(query))
    ranked = []
    for chunk, score in zip(CORPUS, scores):
        if chunk["scheme"] not in allowed or score <= 0:
            continue
        if chunk["doc_type"] in preferred:
            score *= BOOST_FACTOR
        ranked.append((score, chunk))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in ranked[:k]]


if __name__ == "__main__":
    # M3 demo. The scheme is given by hand here; guardrails will detect it in M4.
    demo = [
        ("Q01", "What is the exit load of HDFC Small Cap Fund?", "small_cap"),
        ("Q04", "What is the lock-in period of HDFC ELSS Tax Saver?", "elss"),
        ("Q05", "What is the minimum SIP for HDFC Small Cap Fund?", "small_cap"),
        ("Q07", "What is the benchmark of HDFC Large Cap Fund?", "large_cap"),
        ("Q12", "How do I download my capital gains statement from HDFC MF?", "general"),
    ]
    for qid, question, scheme in demo:
        print(f"\n=== {qid}: {question}  [scheme: {scheme}]")
        for rank, chunk in enumerate(search(question, scheme)[:3], start=1):
            print(f"{rank}. {chunk['chunk_id']} ({chunk['source_id']}, {chunk['doc_type']})")
            print(f"   {chunk['text'][:200]}")
