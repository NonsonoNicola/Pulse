from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, events, checkin, status, trends, crew, chat, emergency, sync, booklet, notify, demo, health
from app.api.deps import set_dependencies
from app.core.config import get_settings
from app.core.db import Database
from app.analysis.service import AnalysisService
from app.events.store import EventStore
from app.llm.client import LLMClient
from app.llm.service import LLMService
from app.rag.store import KnowledgeBase


settings = get_settings()
data_dir = settings.data_dir
data_dir.mkdir(parents=True, exist_ok=True)
(data_dir / "booklet").mkdir(parents=True, exist_ok=True)

db = Database(settings.db_path)
analysis = AnalysisService(db, settings)
event_store = EventStore(db)
kb = KnowledgeBase(db)
llm_client = LLMClient(settings)
llm_service = LLMService(db, settings, analysis, event_store, kb, llm_client)

# Index KB on startup
kb.index()

# Set dependencies for API modules
set_dependencies(db, analysis, event_store, kb, llm_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    db.close()


app = FastAPI(title="Pulse", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for booklet export
app.mount("/booklet-files", StaticFiles(directory=str(data_dir / "booklet")), name="booklet")

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(checkin.router)
app.include_router(status.router)
app.include_router(trends.router)
app.include_router(crew.router)
app.include_router(chat.router)
app.include_router(emergency.router)
app.include_router(sync.router)
app.include_router(booklet.router)
app.include_router(notify.router)
app.include_router(demo.router)