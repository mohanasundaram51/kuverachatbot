"""answer(question): the full flow from PROMPT.md section 8."""

import re

import guardrails
import retriever
from prompts import PROMPT_B_ANSWER

MAX_SENTENCES = 3
TOP_K = 5

TRY_AGAIN = {
    "type": "error",
    "answer": "Sorry, I couldn't reach the answer service just now. Please try again in a minute.",
    "source_url": "",
    "last_updated": "",
}

# Abbreviations that end with a dot but do not end a sentence
ABBREVIATIONS = ("Rs.", "Re.", "Mr.", "Mrs.", "Ms.", "Dr.", "No.", "i.e.", "e.g.", "viz.", "Ltd.")


def limit_sentences(text, max_sentences=MAX_SENTENCES):
    """Keep at most max_sentences sentences (enforced in code, not only in the prompt)."""
    pieces = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = []
    for piece in pieces:
        if sentences and sentences[-1].endswith(ABBREVIATIONS):
            sentences[-1] += " " + piece
        else:
            sentences.append(piece)
    return " ".join(sentences[:max_sentences])


def remove_urls(text):
    """The LLM never supplies links; drop any it writes anyway."""
    return re.sub(r"\s*(https?://|www\.)\S+", "", text).strip()


def answer(question):
    """Returns {"type", "answer", "source_url", "last_updated"}."""
    try:
        # Steps 1-3: PII check, intent check, scheme
        decision = guardrails.check(question)
        if decision["reply"]:
            return decision["reply"]

        # Step 4: top 5 chunks for that scheme + General/All
        chunks = retriever.search(question, decision["scheme"], k=TOP_K)
        if not chunks:
            return guardrails.fixed_reply("not_in_sources")

        # Step 5: Prompt B writes the answer from those chunks only
        context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in chunks)
        prompt = PROMPT_B_ANSWER.replace("{context}", context).replace("{question}", question)
        result = guardrails.call_gemini_json(prompt)
    except Exception:
        return TRY_AGAIN

    # Step 6: code checks. The chunk id must be one of the chunks we sent.
    sent = {c["chunk_id"]: c for c in chunks}
    source_id = str(result.get("source_id", "")).strip()
    text = limit_sentences(remove_urls(str(result.get("answer", ""))))
    if result.get("found") is not True or source_id not in sent or not text:
        return guardrails.fixed_reply("not_in_sources")

    # Step 7: code (not the LLM) looks up the link and date of that chunk
    cited = sent[source_id]
    return {
        "type": "answer",
        "answer": text,
        "source_url": cited["url"],
        "last_updated": guardrails.source_date(cited),
    }
