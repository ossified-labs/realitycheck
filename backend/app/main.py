"""FastAPI entry point.  Run:  uvicorn app.main:app --reload  (from backend/)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from .config import get_settings
from .database import Database
from .services.llm import ClaudeLLM
from .services.pipeline import build_graph, run_investigation
from .services.report import report_to_markdown
from .services.search import TavilySearch

logging.basicConfig(level=logging.INFO)
settings = get_settings()
db = Database(settings.database_path)

app = FastAPI(title="RealityCheck API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


class ClaimIn(BaseModel):
    claim: str = Field(..., min_length=8)

    @field_validator("claim")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) > settings.max_claim_chars:
            raise ValueError(f"Claim must be at most {settings.max_claim_chars} characters")
        return v


def _require(inv_id: str) -> dict:
    inv = db.get_investigation(inv_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return inv


def _job(inv_id: str) -> None:
    try:
        llm = ClaudeLLM(settings.anthropic_api_key, settings.anthropic_model)
        search = TavilySearch(settings.tavily_api_key)
    except Exception as exc:
        db.set_status(inv_id, "failed", error=str(exc))
        return
    run_investigation(db, llm, search, settings, inv_id)


@app.get("/api/health")
def health():
    return {"ok": True, "llm_configured": bool(settings.anthropic_api_key),
            "search_configured": bool(settings.tavily_api_key)}


@app.post("/api/investigations", status_code=202)
def create_investigation(body: ClaimIn, background: BackgroundTasks):
    # Simple global rate limit for the MVP; replace with per-user limits once you add auth.
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if db.count_recent(since) >= settings.rate_limit_per_hour:
        raise HTTPException(429, "Rate limit reached, try again later")
    inv_id = db.create_investigation(body.claim)
    background.add_task(_job, inv_id)  # runs after the response, in a worker thread
    return {"id": inv_id, "status": "queued"}


@app.get("/api/investigations")
def list_investigations():
    return db.list_investigations()


@app.get("/api/investigations/{inv_id}")
def get_investigation(inv_id: str):
    inv = _require(inv_id)
    return {**inv, "subclaims": db.get_subclaims(inv_id)}


@app.get("/api/investigations/{inv_id}/sources")
def get_sources(inv_id: str):
    _require(inv_id)
    return {"sources": db.get_sources(inv_id), "evidence": db.get_evidence(inv_id)}


@app.get("/api/investigations/{inv_id}/graph")
def get_graph(inv_id: str):
    _require(inv_id)
    return build_graph(db, inv_id)


@app.get("/api/investigations/{inv_id}/report")
def get_report(inv_id: str):
    inv = _require(inv_id)
    if not inv.get("report"):
        raise HTTPException(409, f"Report not ready (status: {inv['status']})")
    return inv["report"]


@app.get("/api/investigations/{inv_id}/report.md", response_class=PlainTextResponse)
def export_report(inv_id: str):
    return report_to_markdown(get_report(inv_id))
