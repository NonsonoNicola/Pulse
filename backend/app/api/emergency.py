from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.deps import get_db, get_event_store
from app.core.timeutil import iso, utcnow
from app.events.store import EventStore


router = APIRouter(prefix="/emergency", tags=["emergency"])


class EmergencyStartIn(BaseModel):
    astronaut_id: str
    protocol_key: str
    reason: str
    initial_vitals: dict[str, Any] | None = None
    initial_symptoms: list[str] = []


class CaseNoteIn(BaseModel):
    case_id: str
    text: str
    priority: int = 1


class CaseNoteOut(BaseModel):
    id: str
    case_id: str
    text: str
    priority: int
    created_at: str


@router.post("/start")
def start_emergency(
    payload: EmergencyStartIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != payload.astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only start emergencies for themselves")
    now = utcnow()
    case_id = f"case:{payload.astronaut_id}:{now.timestamp()}"
    db = get_db()
    db.execute(
        "INSERT INTO cases (id, astronaut_id, level, status, title, protocol_id, opened_at, updated_at, notes) "
        "VALUES (?, ?, 'red', 'open', ?, ?, ?, ?, '[]')",
        (case_id, payload.astronaut_id, f"Emergency: {payload.reason}", payload.protocol_key, iso(now), iso(now)),
    )
    # Create SBAR packet
    sbar_id = f"sbar:{case_id}:{now.timestamp()}"
    sbar_payload = {
        "case_id": case_id,
        "astronaut_id": payload.astronaut_id,
        "situation": payload.reason,
        "background": payload.initial_vitals or {},
        "assessment": "Emergency protocol initiated",
        "recommendation": f"Follow {payload.protocol_key} protocol; await ground guidance",
    }
    db.execute(
        "INSERT INTO sbars (id, case_id, astronaut_id, priority, payload, markdown, created_at) "
        "VALUES (?, ?, ?, 4, ?, ?, ?)",
        (sbar_id, case_id, payload.astronaut_id, json.dumps(sbar_payload), "", iso(now)),
    )
    db.execute(
        "UPDATE cases SET sbar_ids = ? WHERE id = ?",
        (json.dumps([sbar_id]), case_id),
    )
    # Queue for sync
    db.execute(
        "INSERT INTO sync_queue (id, kind, ref_id, priority, payload, status, created_at) "
        "VALUES (?, 'case', ?, 4, ?, 'queued', ?)",
        (f"sync:{case_id}", case_id, json.dumps({"case_id": case_id, "sbar_id": sbar_id}), iso(now)),
    )
    # Log event
    store.append_system(
        "case_opened",
        {"case_id": case_id, "protocol": payload.protocol_key, "reason": payload.reason},
        astronaut_id=payload.astronaut_id,
        actor_id=user["id"],
    )
    return {"case_id": case_id, "sbar_id": sbar_id, "status": "open"}


@router.get("/cases")
def list_cases(
    user: dict = Depends(get_current_user),
):
    """List cases for the ground console. Astronauts only see their own cases."""
    db = get_db()
    if user["role"] == "astronaut":
        rows = db.query(
            "SELECT * FROM cases WHERE astronaut_id = ? ORDER BY opened_at DESC",
            (user.get("astronaut_id"),),
        )
    else:
        rows = db.query("SELECT * FROM cases ORDER BY opened_at DESC")
    out = []
    for row in rows:
        case = dict(row)
        case["notes"] = json.loads(case.get("notes") or "[]")
        case["sbar_ids"] = json.loads(case.get("sbar_ids") or "[]")
        out.append(case)
    return out


@router.get("/cases/{case_id}")
def get_case(
    case_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    row = db.query_one("SELECT * FROM cases WHERE id = ?", (case_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    case = dict(row)
    case["notes"] = json.loads(case["notes"])
    case["sbar_ids"] = json.loads(case["sbar_ids"])
    return case


@router.post("/cases/{case_id}/notes", response_model=CaseNoteOut)
def add_case_note(
    case_id: str,
    payload: CaseNoteIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    db = get_db()
    row = db.query_one("SELECT * FROM cases WHERE id = ?", (case_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    from app.core.timeutil import iso, utcnow
    now = utcnow()
    note_id = f"note:{case_id}:{now.timestamp()}"
    notes = json.loads(row["notes"])
    notes.append({
        "id": note_id,
        "text": payload.text,
        "author_id": user["id"],
        "priority": payload.priority,
        "at": iso(now),
        "from_ground": user["role"] in {"ground", "admin"},
    })
    db.execute("UPDATE cases SET notes = ?, updated_at = ? WHERE id = ?", (json.dumps(notes), iso(now), case_id))
    store.append_system(
        "case_note",
        {"case_id": case_id, "note_id": note_id, "text": payload.text, "priority": payload.priority},
        astronaut_id=row["astronaut_id"],
        actor_id=user["id"],
    )
    return CaseNoteOut(id=note_id, case_id=case_id, text=payload.text, priority=payload.priority, created_at=iso(now))


@router.get("/cases/{case_id}/sbar")
def get_sbar_packets(
    case_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    rows = db.query("SELECT * FROM sbars WHERE case_id = ? ORDER BY created_at ASC", (case_id,))
    out = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        out.append(item)
    return {"sbar_packets": out}


@router.post("/cases/{case_id}/sbar")
def generate_sbar(
    case_id: str,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    db = get_db()
    row = db.query_one("SELECT * FROM cases WHERE id = ?", (case_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    from app.api.deps import get_analysis, get_kb

    analysis = get_analysis()
    kb = get_kb()
    now = utcnow()
    bundle = analysis.bundle("en")
    snap = bundle.snapshot(row["astronaut_id"])
    protocol = kb.protocol(row["protocol_id"]) if row["protocol_id"] else {}
    markdown = f"""# SBAR Packet
**Case:** {case_id}
**Astronaut:** {snap.name} ({snap.astronaut_id})
**Protocol:** {protocol.get('title', row['protocol_id'])}
**Priority:** Urgent
**Generated:** {iso(now)}

## Situation
Emergency protocol activated. Level: Red.

## Background
Vitals and context from onboard assessment.

## Assessment
Red-level emergency requiring immediate protocol execution.

## Recommendation
Follow {row['protocol_id']} protocol. Await ground guidance.

---
*Research prototype — not a medical device.*
"""
    sbar_id = f"sbar:{case_id}:{now.timestamp()}"
    sbar_payload = {
        "case_id": case_id,
        "astronaut_id": row["astronaut_id"],
        "situation": "Emergency protocol activated",
        "background": {},
        "assessment": "Red-level emergency",
        "recommendation": f"Follow {row['protocol_id']} protocol; await ground guidance",
    }
    db.execute(
        "INSERT INTO sbars (id, case_id, astronaut_id, priority, payload, markdown, created_at) "
        "VALUES (?, ?, ?, 4, ?, ?, ?)",
        (sbar_id, case_id, row["astronaut_id"], json.dumps(sbar_payload), markdown, iso(now)),
    )
    db.execute(
        "UPDATE cases SET sbar_ids = json_insert(sbar_ids, '$[#]', ?) WHERE id = ?",
        (sbar_id, case_id),
    )
    store.append_system(
        "sbar_packet",
        {"case_id": case_id, "sbar_id": sbar_id},
        astronaut_id=row["astronaut_id"],
        actor_id=user["id"],
    )
    return {"sbar_id": sbar_id, "markdown": markdown}