# HDFC Mutual Fund - Facts Assistant (for Kuvera users)

A small chatbot that answers **factual** questions about three HDFC Mutual Fund schemes, using only official public documents. Every answer shows one source link and a "Last updated from sources" date. It refuses advice, return/performance questions and personal data.

> **Sources decide, the LLM only writes.** Facts come only from retrieved source text. The LLM rewrites that text into a short answer; it never adds its own facts and never writes URLs.

## 1. Problem and who it helps

Kuvera users often have quick factual questions about a fund - "What is the exit load?", "Is there a lock-in?", "What is the benchmark?". The answers are buried in long official PDFs (a Key Information Memorandum is 60,000+ characters). General AI chatbots answer quickly but can invent numbers, mix up schemes, or drift into advice.

This assistant gives Kuvera users a short answer taken word-for-word from HDFC Mutual Fund's own documents, with a link so they can check it themselves. It helps first-time and DIY investors who want facts, not recommendations.

## 2. Scope

- **Product:** Kuvera
- **AMC:** HDFC Mutual Fund
- **Schemes:**

| Scheme | Also recognised as |
|---|---|
| HDFC Large Cap Fund | large cap, largecap, top 100, top100 (old name: HDFC Top 100 Fund) |
| HDFC Small Cap Fund | small cap, smallcap |
| HDFC ELSS Tax Saver | elss, tax saver, taxsaver, tax-saver |

Anything else (other HDFC schemes, other AMCs, unrelated topics) gets the "not in my sources" reply.

## 3. Live demo

Live link: *coming in M10 (Vercel)*

## 4. How it works

```
Chat page (public/index.html) sends:  POST /api/ask  {"question": "..."}
  |
  BACKEND (api/index.py -> pipeline.py)
  1. PII check (regex) ...................... PII found? -> PII reply. STOP.
  |
  2. Intent check (Prompt A) ................ advice / performance / out of scope? -> fixed reply. STOP.
  |
  3. Find the scheme (alias table in code, Prompt A as backup)
  |                                            fact question but no scheme? -> clarify reply. STOP.
  |
  4. Retrieve top 5 chunks (BM25) from data/corpus.json, only from that scheme + "General"/"All" sources
  |
  5. Write the answer (Prompt B) ............ not found? -> not-in-sources reply. STOP.
  |
  6. Code checks: chunk id is valid, answer cut to max 3 sentences
  |
  7. Code adds the source link and date
  |
Backend returns:  {"type": "...", "answer": "...", "source_url": "...", "last_updated": "..."}
Chat page prints exactly what it received. No logic on the page.
```

| File | Layer | What it does |
|---|---|---|
| `ingest.py` | data | Downloads the sources (Mac only) and saves text chunks to `data/corpus.json` |
| `retriever.py` | retrieval | BM25 keyword search with a scheme filter and doc-type boost |
| `guardrails.py` | guardrails | PII regex, scheme aliases, intent check (Prompt A), fixed replies |
| `prompts.py` | generation | Prompt A (intent) and Prompt B (answer) |
| `pipeline.py` | generation | `answer(question)`: the full flow above |
| `api/index.py` | backend API | `GET /api/health`, `POST /api/ask` |
| `public/index.html` | frontend | The chat page (display only) |
| `run_eval.py` | evaluation | Runs the 30 test questions and saves `eval_results.csv` |

**Stack:** Python 3.12, FastAPI, rank-bm25, Google Gemini (`gemini-3.8-flash`, temperature 0, JSON output) via `google-genai`, one plain HTML page, deployed on Vercel.

## 5. Setup (run it locally)

You need Python 3.11+ and a Gemini API key from [Google AI Studio](https://aistudio.google.com).

```bash
# 1. Create the virtual environment and install libraries
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# 2. Add your key: create a file called .env containing one line
#    GEMINI_API_KEY=your-key-here
#    (.env is in .gitignore, so it is never committed)

# 3. Start the app, then open http://127.0.0.1:8000
.venv/bin/uvicorn api.index:app --port 8000

# Optional: rebuild data/corpus.json from the sources
.venv/bin/python ingest.py

# Optional: run the 30-question evaluation
.venv/bin/python run_eval.py
```

## 6. Sources

All sources are official HDFC Mutual Fund documents listed in `sources.csv`. "In corpus" means the text was downloaded and can be used to answer.

| id | Organisation | Document | Scheme | Date on document | In corpus |
|---|---|---|---|---|---|
| S01 | HDFC | [KIM](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Large%20Cap%20Fund%20dated%20November%2021%2C%202025_0.pdf?VersionId=XuOtUPPEfOmbQpuzxBMGCAdqsTmowMh4) | Large Cap | 2025-11-21 | yes (64 chunks) |
| S02 | HDFC | [KIM](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20Small%20Cap%20Fund%20dated%20November%2021%2C%202025_0.pdf?VersionId=pPEndNLX7BQsCy41dKIvauo_DlRvI59A) | Small Cap | 2025-11-21 | yes (64 chunks) |
| S03 | HDFC | [KIM](https://files.hdfcfund.com/s3fs-public/KIM/2025-11/KIM%20-%20HDFC%20ELSS%20Tax%20Saver%20dated%20November%2021%2C%202025_0.pdf?VersionId=CWvBjiK_hIuApMLzaZJVRt17Sc6tmlog) | ELSS | 2025-11-21 | yes (62 chunks) |
| S04 | HDFC | [Scheme page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct) | Large Cap | live page | no (site returned 403) |
| S05 | HDFC | [Scheme page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap-fund/direct) | Small Cap | live page | no (site returned 403) |
| S06 | HDFC | [Scheme page](https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct) | ELSS | live page | no (site returned 403) |
| S07 | HDFC | [Factsheets index](https://www.hdfcfund.com/mutual-funds/factsheets) | All | live page | no (site returned 403) |
| S08 | HDFC | [TER disclosure](https://www.hdfcfund.com/statutory-disclosure/total-expense-ratio-of-mutual-fund-schemes/reports) | All | live page | no (site returned 403) |
| S09 | HDFC | [Statement download](https://www.hdfcfund.com/services/consolidated-account-statement) | General | live page | no (site returned 403) |
| S10 | HDFC | [FAQs](https://www.hdfcfund.com/services/faqs) | General | live page | no (site returned 403) |
| S11 | HDFC | [Fund Facts](https://files.hdfcfund.com/s3fs-public/Others/2026-07/Fund%20Facts%20-%20HDFC%20Large%20Cap%20Fund_July%2026.pdf) | Large Cap | 2026-07 | yes (7 chunks) |
| S12 | HDFC | [Fund Facts](https://files.hdfcfund.com/s3fs-public/Others/2026-07/Fund%20Facts%20-%20HDFC%20Small%20Cap%20Fund_July%2026.pdf) | Small Cap | 2026-07 | yes (7 chunks) |
| S13 | HDFC | [Fund Facts](https://files.hdfcfund.com/s3fs-public/Others/2026-07/Fund%20Facts%20-%20HDFC%20TaxSaver%20Fund_July%2026.pdf) | ELSS | 2026-07 | yes (7 chunks) |

**Date rule:** each answer shows the cited source's `date_on_document`; for a live page it shows `date_fetched`.

## 7. Sample Q&A

Real outputs from `run_eval.py`, not edited. Full version with links: [`sample_qa.md`](sample_qa.md).

| Kind | Question | Type | Answer | Last updated |
|---|---|---|---|---|
| Fact | What is the exit load of HDFC Small Cap Fund? | `answer` | An Exit Load of 1.00% is payable for HDFC Small Cap Fund if Units are redeemed or switched-out within 1 year from the date of allotment. No Exit Load is payable if Units are redeemed or switched-out after 1 year from the date of allotment. | 2025-11-21 |
| Fact | What is the lock-in period of HDFC ELSS Tax Saver? | `answer` | HDFC ELSS Tax Saver has a statutory lock in of 3 years. | 2025-11-21 |
| Fact | What is the benchmark of HDFC Large Cap Fund? | `answer` | The benchmark of HDFC Large Cap Fund is NIFTY 100 Total Returns Index (TRI). | 2026-07 |
| Fact (old name) | Exit load of HDFC Top 100 Fund? | `answer` | An Exit Load of 1.00% is payable if Units are redeemed / switched-out within 1 year from the date of allotment for HDFC Large Cap Fund (formerly known as HDFC Top 100 Fund). No Exit Load is payable if Units are redeemed / switched-out after 1 year from the date of allotment. | 2025-11-21 |
| Process | How do I download my capital gains statement from HDFC MF? | `not_in_sources` | I don't have that in my official sources. I only cover HDFC Large Cap Fund, HDFC Small Cap Fund and HDFC ELSS Tax Saver. | 2026-10-25 |
| Advice | Should I invest in HDFC Small Cap Fund? | `advice` | I can only share factual information about these schemes, not investment advice. To learn how to evaluate mutual funds, see AMFI's investor education page. | 2026-10-25 |
| Performance | What were the 3-year returns of HDFC Large Cap Fund? | `performance` | I don't share or calculate returns. You can see official performance figures in the scheme's latest Fund Facts. | 2026-07 |
| PII | My PAN is ABCDE1234F - show my HDFC folio | `pii` | For your safety, please don't share personal details like PAN, Aadhaar, account numbers, OTPs, email or phone. I can't access accounts; for account help, please use HDFC Mutual Fund's official channels. | 2026-10-25 |
| Not in sources | What is the expense ratio of HDFC Mid Cap Fund? | `not_in_sources` | I don't have that in my official sources. I only cover HDFC Large Cap Fund, HDFC Small Cap Fund and HDFC ELSS Tax Saver. | 2026-10-25 |
| Clarify | What's the exit load? | `clarify` | Which scheme do you mean: HDFC Large Cap Fund, HDFC Small Cap Fund, or HDFC ELSS Tax Saver? | 2026-10-25 |

## 8. Disclaimer

```
Facts-only. No investment advice.
This assistant shares factual information about selected HDFC Mutual Fund schemes using official public sources (HDFC Mutual Fund, AMFI, SEBI). It does not recommend, compare, or predict returns. Mutual fund investments are subject to market risks; read all scheme-related documents carefully.
```

## 9. Design decisions

- **Why refusals are templates.** Advice, performance, PII, not-in-sources and clarify replies are fixed text written in code. The LLM cannot be talked into a different refusal, cannot soften it into advice, and every refusal is identical and testable.
- **Why code picks the URL.** The LLM only returns the id of the chunk it used (e.g. `S02-c57`). Code checks that id was one of the 5 chunks it sent, then looks up that chunk's URL and date from `sources.csv` (via `corpus.json`). An LLM can invent or mistype a link; a lookup cannot. If the id is not one we sent, the answer is treated as "not found". Any URL the LLM writes in its text is removed.
- **Why PII is checked before the LLM.** The regex check is the first line of the flow. If a PAN, Aadhaar, mobile, email, OTP or account/folio number is found, the LLM is never called, so the personal data never leaves our server, and the message is not saved or logged. The page then replaces the message with "[message removed: contained personal information]".
- **Why BM25.** The questions are about exact terms ("exit load", "lock-in", "benchmark") in a small corpus (211 chunks). Keyword search is fast, free, needs no database or embeddings, and is easy to debug: you can see exactly why a chunk ranked first. A scheme filter stops one fund's numbers leaking into another fund's answer.
- **Why the page has no logic.** The page only sends the question and prints the reply. Anyone can open a browser's developer tools and change or skip page code, so a check on the page protects nothing. All checks live in the backend, where users cannot change them. The page also stores nothing: no localStorage, no cookies; refreshing clears the chat.

## 10. Evaluation results

`run_eval.py` runs the 30 questions in `eval_questions.csv` through the same `answer()` function the API uses, and checks: type matches bucket, max 3 sentences, link present, date present. Results: [`eval_results.csv`](eval_results.csv).

| Bucket | Passed |
|---|---|
| fact | 9/14 |
| not in corpus | 3/4 |
| advice | 5/5 |
| performance | 3/3 |
| PII | 3/3 |
| ambiguous | 1/1 |
| **Total** | **24/30 (80%)** |

All 6 failures are on "type matches bucket" only; every reply had at most 3 sentences, a link and a date. No failure is a wrong fact: when the bot did not have the fact, it said so instead of guessing. See Known limits.

## 11. Known limits

- **HDFC web pages could not be downloaded.** All 7 `www.hdfcfund.com` pages (S04-S10: scheme pages, factsheets index, TER page, statement page, FAQs) return "403 Forbidden" to automated downloads. Only the 6 PDFs are in the corpus. The fixed replies still link to S07 and S10, but their text is not used for answers.
- **Statement download steps (Q12)** were only on S09, so process questions about statements get "not in my sources".
- **Riskometer level (Q09)** is shown as an image in the PDFs, so the text "Very High" is not in the corpus.
- **"What is a riskometer?" (Q11)** - there is no AMFI or SEBI source in `sources.csv`, so general concept questions have nothing to search.
- **Minimum SIP (Q05, Q06)** - the KIM states a "Minimum Application Amount" (Rs.100 / Rs.500), not a minimum SIP, so the bot does not claim one.
- **NAV today (Q18)** gets the performance reply (product rule 3: no NAV), while the eval file expected "not in corpus". The behaviour follows the product rules.
- **The advice reply** says "see AMFI's investor education page" (wording fixed by the spec), but `sources.csv` has no AMFI page, so it links to HDFC Mutual Fund's FAQs (S10).
- **Snapshot, not live.** Answers come from documents saved on 2026-10-25 (KIMs dated 2025-11-21, Fund Facts July 2026). If HDFC updates a document, `ingest.py` must be re-run and `data/corpus.json` committed again.
- **Keyword search only.** BM25 matches words, not meaning; a question phrased very differently from the document may miss the right chunk.
- **LLM dependence.** Intent and answer writing use Gemini. If Gemini is busy or down, the bot replies "please try again". Gemini can occasionally pick a different but equally valid chunk for the same question.
