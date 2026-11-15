from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.deps import get_db


router = APIRouter(prefix="/sync", tags=["sync"])


class SyncConfigIn(BaseModel):
    rtt_seconds: float
    mode: str | None = None  # live, async, assisted, full


@router.get("/queue")
def sync_queue(
    status: str | None = Query(None),
    limit: int = Query(100, le=500),
    user: dict = Depends(get_current_user),
):
    if user["role"] not in {"ground", "admin", "cmo"}:
        raise HTTPException(status_code=403, detail="Only ground/CMO/admin can view sync queue")
    db = get_db()
    clauses = []
    params = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = db.query(
        f"SELECT * FROM sync_queue{where} ORDER BY priority DESC, created_at ASC LIMIT ?",
        (*params, limit),
    )
    return [dict(r) for r in rows]


@router.post("/flush")
def flush_sync(
    user: dict = Depends(get_current_user),
):
    if user["role"] not in {"ground", "admin", "cmo"}:
        raise HTTPException(status_code=403, detail="Only ground/CMO/admin can flush sync queue")
    # In the demo, this just marks queued items as sent
    from app.core.timeutil import iso, utcnow
    db = get_db()
    now = iso(utcnow())
    db.execute(
        "UPDATE sync_queue SET status = 'sent', sent_at = ? WHERE status = 'queued'",
        (now,),
    )
    return {"flushed": True, "at": now}


@router.get("/link/status")
def link_status(
    user: dict = Depends(get_current_user),
):
    # Every authenticated crew member may read the link state: the emergency
    # page shows it read-only for astronauts and the CMO. Only ground/admin can
    # change it.
    db = get_db()
    row = db.query_one("SELECT value FROM settings WHERE key = 'link_config'")
    if row:
        import json
        return json.loads(row["value"])
    return {
        "mode": "live",
        "rtt_seconds": 5,
        "last_contact": None,
        "autonomy_mode": "live",
        "description": "Ground link active (simulated)",
    }


@router.post("/link/config")
def link_config(
    payload: SyncConfigIn,
    user: dict = Depends(get_current_user),
):
    if user["role"] not in {"ground", "admin"}:
        raise HTTPException(status_code=403, detail="Only ground/admin can configure link")
    import json
    from app.core.timeutil import iso, utcnow
    db = get_db()
    config = {
        "mode": payload.mode or ("live" if payload.rtt_seconds < 30 else "async" if payload.rtt_seconds < 1800 else "assisted" if payload.rtt_seconds < 86400 else "full"),
        "rtt_seconds": payload.rtt_seconds,
        "last_contact": iso(utcnow()),
        "description": f"Simulated link: {payload.rtt_seconds:.0f}s RTT",
    }
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('link_config', ?)",
        (json.dumps(config),),
    )
    return config