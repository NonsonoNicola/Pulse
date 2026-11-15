from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.api.deps import get_db, get_event_store
from app.core.db import Database
from app.events.schemas import EVENT_TYPES, EventIn, EventOut
from app.events.store import EventStore


router = APIRouter(prefix="/events", tags=["events"])


class EventBatchIn(BaseModel):
    events: list[EventIn]


class EventBatchOut(BaseModel):
    results: list[dict[str, Any]]


@router.post("", response_model=EventOut)
def append_event(
    event: EventIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    record, _ = store.append(event, actor_id=user["id"])
    return record


@router.post("/batch", response_model=EventBatchOut)
def append_batch(
    batch: EventBatchIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    results = store.append_many(batch.events, actor_id=user["id"])
    return EventBatchOut(results=[{"event": r[0], "created": r[1]} for r in results])


@router.get("", response_model=list[EventOut])
def list_events(
    astronaut_id: str | None = Query(None),
    types: list[str] | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(500, le=2000),
    offset: int = Query(0, ge=0),
    ascending: bool = Query(True),
    store: EventStore = Depends(get_event_store),
):
    return store.list(
        astronaut_id=astronaut_id,
        types=types,
        start=start,
        end=end,
        limit=limit,
        offset=offset,
        ascending=ascending,
    )


@router.get("/types")
def event_types():
    return {"types": sorted(EVENT_TYPES)}


@router.get("/counts")
def event_counts(store: EventStore = Depends(get_event_store)):
    return {"total": store.count(), "by_type": store.count_by_type()}