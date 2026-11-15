from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.deps import get_event_store
from app.events.schemas import CheckinIn, EventIn, SkipIn
from app.events.store import EventStore
from app.core.timeutil import utcnow


router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.post("")
def submit_checkin(
    payload: CheckinIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    if not user.get("astronaut_id"):
        raise HTTPException(status_code=403, detail="Only astronauts can check in")
    event = EventIn(
        idempotency_key=f"checkin:{user['astronaut_id']}:{payload.measured_at or utcnow().isoformat()}",
        astronaut_id=user["astronaut_id"],
        type="checkin",
        measured_at=payload.measured_at or utcnow(),
        source="manual",
        payload=payload.model_dump(exclude={"measured_at", "idempotency_key"}),
    )
    record, _ = store.append(event, actor_id=user["id"])
    return {"event": record}


@router.post("/skip")
def skip_checkin(
    payload: SkipIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    if not user.get("astronaut_id"):
        raise HTTPException(status_code=403, detail="Only astronauts can skip check-in")
    event = EventIn(
        idempotency_key=f"skip:{user['astronaut_id']}:{payload.measured_at or utcnow().isoformat()}",
        astronaut_id=user["astronaut_id"],
        type="skipped_checkin",
        measured_at=payload.measured_at or utcnow(),
        source="manual",
        payload=payload.model_dump(exclude={"measured_at"}),
    )
    record, _ = store.append(event, actor_id=user["id"])
    return {"event": record}


@router.get("/symptoms")
def symptom_catalog(locale: str = "en"):
    from app.core.config import load_symptoms
    data = load_symptoms()
    symptoms = data.get("symptoms", [])
    out = []
    for s in symptoms:
        out.append(
            {
                "id": s["id"],
                "label": s.get(f"label_{locale}") or s.get("label_en") or s.get("en") or s["id"],
                "group": s.get("group", "general"),
            }
        )
    return {"symptoms": out}