"""Decide "answer or refuse" before any answer is written.

1. PII check (regex, no LLM)
2. Scheme alias table (code)
3. Intent check (Prompt A, Gemini)
4. Fixed replies (code, no LLM)
"""

import csv
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from prompts import PROMPT_A_INTENT

load_dotenv()

MODEL = "gemini-3.8-flash"
SOURCES_PATH = Path(__file__).parent / "sources.csv"

# ---------------------------------------------------------------- 1. PII check

PII_PATTERNS = {
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "aadhaar": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "mobile": r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}\b",
    "email": r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",
    "otp": r"\bOTP\b\D{0,20}\d{4,8}\b|\b\d{4,8}\D{0,20}\bOTP\b",
    "account": r"\b(?:account|a/c|folio)\b\D{0,20}\d{6,}",
}


def contains_pii(question):
    """True if the question looks like it holds personal data. Runs before any LLM call."""
    return any(re.search(p, question, re.IGNORECASE) for p in PII_PATTERNS.values())


# ------------------------------------------------------- 2. Scheme alias table

SCHEME_NAMES = {
    "large_cap": "HDFC Large Cap Fund",
    "small_cap": "HDFC Small Cap Fund",
    "elss": "HDFC ELSS Tax Saver",
}

SCHEME_ALIASES = {
    "large_cap": ["large cap", "largecap", "top 100", "top100"],
    "small_cap": ["small cap", "smallcap"],
    "elss": ["elss", "tax saver", "taxsaver", "tax-saver"],
}


def scheme_from_aliases(question):
    """The one scheme named in the question, or None if zero or several are named."""
    q = question.lower()
    found = [key for key, aliases in SCHEME_ALIASES.items() if any(a in q for a in aliases)]
    return found[0] if len(found) == 1 else None


# --------------------------------------------------------- 3. Intent check (A)

_client = None


def call_gemini_json(prompt):
    """Send a prompt to Gemini (temperature 0, JSON output) and return the parsed JSON."""
    global _client
    from google import genai
    from google.genai import types

    if _client is None:
        # 30-second limit and at most 3 tries, so a busy Gemini can never freeze the app
        _client = genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(timeout=30_000, retry_options=types.HttpRetryOptions(attempts=3)),
        )
    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    return json.loads(response.text)


def classify(question):
    """Prompt A. Returns {"intent": ..., "scheme": ...}."""
    result = call_gemini_json(PROMPT_A_INTENT.replace("{question}", question))
    intent = result.get("intent")
    scheme = result.get("scheme")
    if intent not in {"fact", "advice", "performance", "out_of_scope"}:
        intent = "out_of_scope"
    if scheme not in {"large_cap", "small_cap", "elss", "general", "unknown"}:
        scheme = "unknown"
    return {"intent": intent, "scheme": scheme}


# ------------------------------------------------------------ 4. Fixed replies

with SOURCES_PATH.open(encoding="utf-8-sig") as f:
    SOURCES = {row["id"].strip(): row for row in csv.DictReader(f)}


def source_date(row):
    """Date rule: date_on_document, or date_fetched for a live page."""
    date = row["date_on_document"].strip()
    return row["date_fetched"].strip() if date.lower() == "live page" else date


FIXED_REPLIES = {
    "advice": "I can only share factual information about these schemes, not investment advice. "
              "To learn how to evaluate mutual funds, see AMFI's investor education page.",
    "performance": "I don't share or calculate returns. You can see official performance figures "
                   "in the scheme's latest Fund Facts.",
    "pii": "For your safety, please don't share personal details like PAN, Aadhaar, account numbers, "
           "OTPs, email or phone. I can't access accounts; for account help, please use "
           "HDFC Mutual Fund's official channels.",
    "not_in_sources": "I don't have that in my official sources. I only cover HDFC Large Cap Fund, "
                      "HDFC Small Cap Fund and HDFC ELSS Tax Saver.",
    "clarify": "Which scheme do you mean: HDFC Large Cap Fund, HDFC Small Cap Fund, "
               "or HDFC ELSS Tax Saver?",
}

# Advice links S10 (HDFC FAQs): sources.csv has no AMFI page (S18).
FIXED_SOURCES = {"advice": "S10", "pii": "S10", "not_in_sources": "S07", "clarify": "S07"}
FUND_FACTS = {"large_cap": "S11", "small_cap": "S12", "elss": "S13"}


def fixed_reply(reply_type, scheme=None):
    if reply_type == "performance":
        source_id = FUND_FACTS.get(scheme, "S07")
    else:
        source_id = FIXED_SOURCES[reply_type]
    row = SOURCES[source_id]
    return {
        "type": reply_type,
        "answer": FIXED_REPLIES[reply_type],
        "source_url": row["url"].strip(),
        "last_updated": source_date(row),
    }


# ------------------------------------------------------------------- Together

def check(question):
    """Run steps 1-3 of the flow.

    Returns {"reply": <fixed reply or None>, "intent": ..., "scheme": ...}.
    If "reply" is None, the question is a fact question for that scheme.
    """
    if contains_pii(question):
        return {"reply": fixed_reply("pii"), "intent": None, "scheme": None}

    label = classify(question)
    intent = label["intent"]
    scheme = scheme_from_aliases(question) or label["scheme"]

    if intent == "advice":
        return {"reply": fixed_reply("advice"), "intent": intent, "scheme": scheme}
    if intent == "performance":
        return {"reply": fixed_reply("performance", scheme), "intent": intent, "scheme": scheme}
    if intent == "out_of_scope":
        return {"reply": fixed_reply("not_in_sources"), "intent": intent, "scheme": scheme}
    if scheme == "unknown":
        return {"reply": fixed_reply("clarify"), "intent": intent, "scheme": scheme}
    return {"reply": None, "intent": intent, "scheme": scheme}
