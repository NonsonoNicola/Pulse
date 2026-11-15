from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.auth import get_current_user
from app.api.deps import get_analysis, get_db, get_event_store
from app.booklet.export import generate_booklet
from app.events.store import EventStore


router = APIRouter(prefix="/booklet", tags=["booklet"])


@router.get("/{astronaut_id}")
def get_booklet(
    astronaut_id: str,
    user: dict = Depends(get_current_user),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only view their own booklet")
    analysis = get_analysis()
    bundle = analysis.bundle("en")
    if astronaut_id not in bundle.snapshots:
        raise HTTPException(status_code=404, detail="Astronaut not found")
    snap = bundle.snapshot(astronaut_id)
    store = EventStore(get_db())
    events = store.all_for(astronaut_id)
    return {
        "profile": {
            "id": snap.astronaut_id,
            "name": snap.name,
            "role_title": snap.role_title,
            "color": snap.color,
        },
        "status": snap.status_payload(),
        "events": events[-200:],
    }


@router.get("/{astronaut_id}/export")
def export_booklet(
    astronaut_id: str,
    user: dict = Depends(get_current_user),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only export their own booklet")
    analysis = get_analysis()
    db = get_db()
    bundle = analysis.bundle("en")
    if astronaut_id not in bundle.snapshots:
        raise HTTPException(status_code=404, detail="Astronaut not found")
    snap = bundle.snapshot(astronaut_id)
    store = get_event_store()
    events = store.all_for(astronaut_id)
    booklet_path = generate_booklet(astronaut_id, snap, events, db)
    return FileResponse(booklet_path, filename=f"booklet_{astronaut_id}.zip")