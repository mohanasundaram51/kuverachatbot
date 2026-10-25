"""Run all questions in eval_questions.csv through answer() and save eval_results.csv.

Run on your Mac:  .venv/bin/python run_eval.py
"""

import csv
import re
import time
from collections import defaultdict

from pipeline import answer

QUESTIONS_CSV = "eval_questions.csv"
RESULTS_CSV = "eval_results.csv"
PAUSE_SECONDS = 1

# bucket in eval_questions.csv (text before any "(") -> type the app should return
EXPECTED_TYPE = {
    "fact": "answer",
    "not in corpus": "not_in_sources",
    "advice": "advice",
    "performance": "performance",
    "PII": "pii",
    "ambiguous": "clarify",
}


def main_bucket(bucket):
    return bucket.split("(")[0].strip()


def count_sentences(text):
    """Independent count: a sentence ends with . ! or ? followed by a space and a capital letter, or the end."""
    text = re.sub(r"\b(Rs|Re|Mr|Mrs|Ms|Dr|No|Ltd|viz|i\.e|e\.g)\.", r"\1", text)
    return len(re.findall(r"[.!?](?=\s+[A-Z(]|\s*$)", text.strip())) or (1 if text.strip() else 0)


def main():
    with open(QUESTIONS_CSV, encoding="utf-8-sig") as f:
        questions = list(csv.DictReader(f))

    results = []
    for q in questions:
        reply = answer(q["question"])
        expected = EXPECTED_TYPE.get(main_bucket(q["bucket"]), "?")
        checks = {
            "type_matches": reply["type"] == expected,
            "max_3_sentences": count_sentences(reply["answer"]) <= 3,
            "link_present": reply["source_url"].startswith("http"),
            "date_present": bool(reply["last_updated"]),
        }
        results.append({
            "id": q["id"],
            "question": q["question"],
            "bucket": q["bucket"],
            "expected_behaviour": q["expected_behaviour"],
            "expected_type": expected,
            "type_returned": reply["type"],
            "answer": reply["answer"],
            "source_url": reply["source_url"],
            "last_updated": reply["last_updated"],
            **{name: "yes" if ok else "NO" for name, ok in checks.items()},
            "pass": "yes" if all(checks.values()) else "NO",
        })
        print(f"{q['id']}  {results[-1]['pass']:<3}  {reply['type']:<15} {q['question']}", flush=True)
        time.sleep(PAUSE_SECONDS)

    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    per_bucket = defaultdict(lambda: [0, 0])
    for r in results:
        b = main_bucket(r["bucket"])
        per_bucket[b][1] += 1
        per_bucket[b][0] += r["pass"] == "yes"
    print(f"\n{'bucket':<15} passed")
    for b, (passed, total) in per_bucket.items():
        print(f"{b:<15} {passed}/{total}")
    total_passed = sum(p for p, _ in per_bucket.values())
    print(f"{'TOTAL':<15} {total_passed}/{len(results)}")
    print(f"\nSaved {RESULTS_CSV}")


if __name__ == "__main__":
    main()
