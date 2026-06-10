"""
api/routes.py
~~~~~~~~~~~~~
FastAPI REST layer for the Recruiting Database Agent.

Endpoints
---------
GET  /            → Serve the web UI (static/index.html)
POST /ask         → Natural language query (Tamil / English / mixed)
GET  /health      → DB and service health check
GET  /stats       → Candidate count by status (for dashboard)
GET  /candidates  → List all candidates (convenience wrapper)
POST /search      → Structured search by role and experience
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from db.connector import DBConnector
from graph import run

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Recruiting Database Agent",
    description=(
        "Multi-agent recruiting assistant powered by LangGraph + Groq. "
        "Supports natural language queries in Tamil, English, and mixed input."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
_STATIC_DIR = Path(__file__).parent.parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Shared DB connector for health checks and stats
_db = DBConnector()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language query")


class AskResponse(BaseModel):
    response:   str
    intent:     str
    entities:   dict[str, Any]
    sql_ran:    str
    confidence: float
    trace:      list[str]
    db_result:  list[dict[str, Any]] = []


class SearchRequest(BaseModel):
    role:       Optional[str]   = Field(None,  description="Job role filter")
    experience: Optional[float] = Field(0.0,   description="Minimum years of experience")
    status:     Optional[str]   = Field(None,  description="Candidate status filter")


class HealthResponse(BaseModel):
    status:  str
    db:      str
    db_mode: str


# ---------------------------------------------------------------------------
# GET / → Serve web UI
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def serve_ui() -> FileResponse:
    """Serve the RecruitAI chat interface."""
    index_path = _STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Web UI not found")
    return FileResponse(str(index_path), media_type="text/html")


# ---------------------------------------------------------------------------
# POST /ask
# ---------------------------------------------------------------------------
@app.post("/ask", response_model=AskResponse, summary="Natural language query")
async def ask(request: AskRequest) -> AskResponse:
    """
    Submit a natural language recruiting query (Tamil, English, or mixed).

    Returns the formatted response, detected intent, extracted entities,
    the SQL that ran, confidence score, execution trace, and raw DB rows.
    """
    try:
        state = run(request.text)
        return AskResponse(
            response=state.get("response", ""),
            intent=state.get("intent", "unknown"),
            entities=state.get("entities", {}),
            sql_ran=state.get("db_query", ""),
            confidence=state.get("confidence", 0.0),
            trace=state.get("trace", []),
            db_result=state.get("db_result", []),
        )
    except Exception as exc:
        logger.error("POST /ask error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    """Returns service status and database connectivity."""
    is_alive = _db.health_check()
    return HealthResponse(
        status="ok",
        db="connected" if is_alive else "error",
        db_mode=_db.mode,
    )


# ---------------------------------------------------------------------------
# GET /stats — candidate counts by status (for dashboard)
# ---------------------------------------------------------------------------
@app.get("/stats", summary="Candidate status statistics")
async def stats() -> dict[str, int]:
    """Returns candidate counts grouped by status."""
    try:
        rows = _db.execute_query(
            "SELECT status, COUNT(*) AS cnt FROM candidates GROUP BY status",
            (),
        )
        result: dict[str, int] = {
            "total": 0,
            "applied": 0,
            "screening": 0,
            "interview": 0,
            "hired": 0,
            "rejected": 0,
        }
        for r in rows:
            status = r.get("status", "")
            cnt    = int(r.get("cnt", 0))
            result[status] = cnt
            result["total"] += cnt
        return result
    except Exception as exc:
        logger.error("GET /stats error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# GET /candidates
# ---------------------------------------------------------------------------
@app.get("/candidates", response_model=AskResponse, summary="List all candidates")
async def candidates() -> AskResponse:
    """Convenience endpoint — returns all candidates ordered by experience."""
    try:
        state = run("show all candidates")
        return AskResponse(
            response=state.get("response", ""),
            intent=state.get("intent", "unknown"),
            entities=state.get("entities", {}),
            sql_ran=state.get("db_query", ""),
            confidence=state.get("confidence", 0.0),
            trace=state.get("trace", []),
            db_result=state.get("db_result", []),
        )
    except Exception as exc:
        logger.error("GET /candidates error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# POST /search
# ---------------------------------------------------------------------------
@app.post("/search", response_model=AskResponse, summary="Structured candidate search")
async def search(request: SearchRequest) -> AskResponse:
    """
    Build a natural language query from structured parameters and run the agent.

    Accepts role, minimum experience, and status filters.
    """
    parts: list[str] = []

    if request.role:
        parts.append(f"find {request.role} candidates")
    else:
        parts.append("show candidates")

    if request.experience and request.experience > 0:
        parts.append(f"with more than {request.experience} years experience")

    if request.status:
        parts.append(f"with status {request.status}")

    natural_query = " ".join(parts) if parts else "show all candidates"

    try:
        state = run(natural_query)
        return AskResponse(
            response=state.get("response", ""),
            intent=state.get("intent", "unknown"),
            entities=state.get("entities", {}),
            sql_ran=state.get("db_query", ""),
            confidence=state.get("confidence", 0.0),
            trace=state.get("trace", []),
            db_result=state.get("db_result", []),
        )
    except Exception as exc:
        logger.error("POST /search error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
