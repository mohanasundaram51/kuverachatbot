"""Backend API for the HDFC Mutual Fund Facts Assistant."""

from fastapi import FastAPI

app = FastAPI(title="HDFC MF Facts Assistant")


@app.get("/api/health")
def health():
    return {"status": "ok"}
