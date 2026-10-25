"""Backend API for the HDFC Mutual Fund Facts Assistant."""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# pipeline.py, guardrails.py etc. live one folder up from api/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import answer  # noqa: E402

MAX_QUESTION_CHARS = 500

app = FastAPI(title="HDFC MF Facts Assistant")


class AskRequest(BaseModel):
    question: str = ""


@app.get("/", include_in_schema=False)
def chat_page():
    # Local use only. On Vercel, vercel.json serves public/index.html at "/".
    return FileResponse(Path(__file__).resolve().parent.parent / "public" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/ask")
def ask(body: AskRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please type a question.")
    if len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Your question is too long. Please keep it under {MAX_QUESTION_CHARS} characters.",
        )
    return answer(question)
