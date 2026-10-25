"""Download every source in sources.csv and save clean text chunks to data/corpus.json.

Runs only on your Mac (never on Vercel):  .venv/bin/python ingest.py
"""

import csv
import io
import json
import re
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

SOURCES_CSV = Path("sources.csv")
CORPUS_JSON = Path("data/corpus.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
TIMEOUT = 30

CHUNK_WORDS = 200  # target chunk size (about 150-250 words)
OVERLAP_WORDS = 40  # words repeated from the previous chunk


def read_sources():
    with SOURCES_CSV.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # Rule 1: skip rows without a real URL
    return [r for r in rows if r.get("url", "").strip().startswith("http")]


def pdf_to_text(data):
    """Page text plus table rows. Table rows are joined with ' | ' so they stay readable."""
    parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()
            boxes = [t.bbox for t in tables]

            def outside_tables(obj):
                x0, top, x1, bottom = obj["x0"], obj["top"], obj["x1"], obj["bottom"]
                return not any(
                    x0 >= b[0] and x1 <= b[2] and top >= b[1] and bottom <= b[3]
                    for b in boxes
                )

            text = page.filter(outside_tables).extract_text() or ""
            parts.append(text)
            for table in tables:
                for row in table.extract():
                    cells = [re.sub(r"\s+", " ", c or "").strip() for c in row]
                    cells = [c for c in cells if c]
                    if cells:
                        parts.append(" | ".join(cells))
    return "\n".join(parts)


def html_to_text(html):
    """Visible page text without menus, scripts, headers and footers."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "header", "footer", "form", "aside", "iframe"]):
        tag.decompose()
    for tag in soup.select('[class*="menu"], [class*="footer"], [class*="navbar"], [id*="menu"], [id*="footer"]'):
        tag.decompose()
    return soup.get_text(separator="\n")


def clean(text):
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def split_into_chunks(text):
    words = text.split()
    chunks = []
    step = CHUNK_WORDS - OVERLAP_WORDS
    for start in range(0, len(words), step):
        piece = words[start:start + CHUNK_WORDS]
        # fold a tiny tail into the previous chunk instead of keeping it alone
        if chunks and len(piece) < 60:
            chunks[-1] = " ".join(words[start - step:start + CHUNK_WORDS])
            break
        chunks.append(" ".join(piece))
        if start + CHUNK_WORDS >= len(words):
            break
    return chunks


def fetch_text(url):
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    is_pdf = "pdf" in resp.headers.get("Content-Type", "").lower() or resp.content[:4] == b"%PDF"
    raw = pdf_to_text(resp.content) if is_pdf else html_to_text(resp.text)
    return clean(raw)


def main():
    corpus = []
    report = []
    for src in read_sources():
        sid = src["id"].strip()
        try:
            text = fetch_text(src["url"].strip())
            error = ""
        except Exception as e:  # report and move on to the next source
            text, error = "", f"{type(e).__name__}: {e}"[:120]

        for n, chunk_text in enumerate(split_into_chunks(text), start=1):
            corpus.append({
                "chunk_id": f"{sid}-c{n}",
                "source_id": sid,
                "url": src["url"].strip(),
                "scheme": src["scheme"].strip(),
                "doc_type": src["doc_type"].strip(),
                "source_org": src["source_org"].strip(),
                "date_on_document": src["date_on_document"].strip(),
                "date_fetched": src["date_fetched"].strip(),
                "text": chunk_text,
            })
        report.append((sid, src["doc_type"], len(text), error))

    CORPUS_JSON.parent.mkdir(exist_ok=True)
    CORPUS_JSON.write_text(json.dumps(corpus, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'id':<5} {'doc_type':<20} {'chars':>7}  status")
    for sid, doc_type, chars, error in report:
        status = f"FAILED - {error}" if error else ("TOO SHORT (<300 chars)" if chars < 300 else "ok")
        print(f"{sid:<5} {doc_type:<20} {chars:>7}  {status}")
    print(f"\nSaved {len(corpus)} chunks to {CORPUS_JSON}")


if __name__ == "__main__":
    main()
