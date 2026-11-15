from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api import auth, events, checkin, status, trends, crew, chat, emergency, sync, booklet, notify, demo, health
from app.core.config import get_settings
from app.core.db import Database
from app.analysis.service import AnalysisService
from app.events.store import EventStore
from app.llm.client import LLMClient
from app.llm.service import LLMService
from app.rag.store import KnowledgeBase


settings = get_settings()
data_dir = settings.data_dir
ground_db_path = settings.ground_db_path
ground_db_path.parent.mkdir(parents=True, exist_ok=True)

ground_db = Database(ground_db_path)
ground_analysis = AnalysisService(ground_db, settings)
ground_event_store = EventStore(ground_db)
ground_kb = KnowledgeBase(ground_db)
ground_llm_client = LLMClient(settings)
ground_llm_service = LLMService(ground_db, settings, ground_analysis, ground_event_store, ground_kb, ground_llm_client)

ground_kb.index()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    ground_db.close()


app = FastAPI(title="Pulse Ground Node", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (subset for ground)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(status.router)
app.include_router(trends.router)
app.include_router(crew.router)
app.include_router(chat.router)
app.include_router(emergency.router)
app.include_router(sync.router)
app.include_router(booklet.router)
app.include_router(notify.router)


# Dependency providers
def get_db() -> Database:
    return ground_db


def get_analysis() -> AnalysisService:
    return ground_analysis


def get_event_store() -> EventStore:
    return ground_event_store


def get_kb() -> KnowledgeBase:
    return ground_kb


def get_llm_service() -> LLMService:
    return ground_llm_service


app.dependency_overrides = {
    "get_db": get_db,
    "get_analysis": get_analysis,
    "get_event_store": get_event_store,
    "get_kb": get_kb,
    "get_llm_service": get_llm_service,
}


@app.get("/", include_in_schema=False)
def root():
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
          <head><meta charset="utf-8"><title>Pulse — Ground Node</title></head>
          <body style="font-family: system-ui, sans-serif; background:#030712; color:#e5e7eb; padding:2rem">
            <h1 style="color:#2dd4bf">Pulse — Ground Node</h1>
            <p>Store-and-forward ground node for the Pulse research prototype.</p>
            <p>This node exposes a JSON API. The flight-surgeon UI is the
              <strong>Ground</strong> page in the main web app (frontend port 5173).</p>
            <p><a style="color:#5eead4" href="/docs">Open the API documentation</a></p>
            <p style="color:#9ca3af">Research prototype — not a medical device.</p>
          </body>
        </html>
        """
    )


@app.get("/ground/cases")
def ground_cases():
    """Ground console: list all cases with sync status."""
    rows = ground_db.query("SELECT * FROM cases ORDER BY opened_at DESC")
    return [dict(r) for r in rows]


@app.get("/ground/sync/queue")
def ground_sync_queue():
    rows = ground_db.query("SELECT * FROM sync_queue ORDER BY priority DESC, created_at ASC")
    return [dict(r) for r in rows]


@app.post("/ground/sync/ack/{sync_id}")
def ground_sync_ack(sync_id: str):
    from app.core.timeutil import iso, utcnow
    ground_db.execute(
        "UPDATE sync_queue SET status = 'acked', acked_at = ? WHERE id = ?",
        (iso(utcnow()), sync_id),
    )
    return {"acked": True}


@app.post("/ground/respond/{case_id}")
def ground_respond(case_id: str, response: dict):
    """Ground flight surgeon responds to a case."""
    from app.core.timeutil import iso, utcnow
    now = utcnow()
    note_id = f"ground_note:{case_id}:{now.timestamp()}"
    row = ground_db.query_one("SELECT * FROM cases WHERE id = ?", (case_id,))
    if not row:
        return {"error": "Case not found"}
    notes = json.loads(row["notes"])
    notes.append({
        "id": note_id,
        "text": response.get("text", ""),
        "author": "ground",
        "priority": response.get("priority", 1),
        "at": iso(now),
        "from_ground": True,
    })
    ground_db.execute("UPDATE cases SET notes = ?, updated_at = ? WHERE id = ?", (json.dumps(notes), iso(now), case_id))
    ground_event_store.append_system(
        "ground_message",
        {"case_id": case_id, "note_id": note_id, "text": response.get("text", "")},
        astronaut_id=row["astronaut_id"],
        actor_id="ground",
        origin_node="ground",
    )
    # Trigger re-evaluation on ground
    ground_analysis.invalidate()
    return {"ok": True, "note_id": note_id}


import json