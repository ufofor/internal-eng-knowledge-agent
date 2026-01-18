from __future__ import annotations

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.knowledge_agent.llm import get_llm
from app.knowledge_agent.rag import RagInput, build_rag_prompt, validate_citations, extract_citations
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional

# Reuse your policy-aware retrieval function
from scripts.query_index_policy import run_policy_query

class AnswerResponse(BaseModel):
    query: str
    answer: str
    citations: List[str] = Field(default_factory=list)
    retrieved: List[Citation]

class Citation(BaseModel):
    doc_id: str
    doc_type: str
    title: str
    source_path: str = ""
    last_updated: str = ""
    score_final: float
    score_sim: float
    reasons: List[str]
    preview: str


class QueryResponse(BaseModel):
    query: str
    top_k: int
    candidates: int
    results: List[Citation]


app = FastAPI(title="Internal Engineering Knowledge Agent", version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/answer", response_model=AnswerResponse)
def answer(
    q: str = Query(..., min_length=3),
    top_k: int = Query(5, ge=1, le=10),
    candidates: int = Query(30, ge=5, le=200),
):
    # 1) Retrieve
    results = run_policy_query(q, top_k=top_k, candidates=candidates)
    if not results:
        return AnswerResponse(query=q, answer="Insufficient information in provided sources.", citations=[], retrieved=[])

    # 2) Build prompt
    rag_inp = RagInput(query=q, retrieved=results)
    prompt = build_rag_prompt(rag_inp)

    # 3) Call LLM
    llm = get_llm()
    draft = llm.complete(prompt)

    # 4) Validate citations
    allowed = [r["doc_id"] for r in results]
    try:
        validate_citations(draft, allowed_ids=allowed)
    except ValueError as e:
        # hard fail => safer than returning hallucinations
        raise HTTPException(status_code=502, detail=f"LLM citation validation failed: {e}")

    cites = extract_citations(draft)

    # 5) Return
    cleaned = []
    for r in results:
        preview = (r.get("preview") or "").replace("\n", " ")
        if len(preview) > 280:
            preview = preview[:280] + "..."
        cleaned.append({**r, "preview": preview})

    return AnswerResponse(query=q, answer=draft, citations=cites, retrieved=cleaned)


@app.get("/query", response_model=QueryResponse)
def query(
    q: str = Query(..., min_length=3, description="User question (natural language)"),
    top_k: int = Query(5, ge=1, le=10),
    candidates: int = Query(30, ge=5, le=200),
):
    try:
        results = run_policy_query(q, top_k=top_k, candidates=candidates)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Query failed: {e}")

    if not results:
        return QueryResponse(query=q, top_k=top_k, candidates=candidates, results=[])

    # Trim preview to keep API responses small and consistent
    cleaned: List[dict] = []
    for r in results:
        preview = (r.get("preview") or "").replace("\n", " ")
        if len(preview) > 280:
            preview = preview[:280] + "..."
        cleaned.append({**r, "preview": preview})

    return QueryResponse(query=q, top_k=top_k, candidates=candidates, results=cleaned)

