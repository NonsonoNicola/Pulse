from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.deps import get_db


router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    user_id: str | None
    astronaut_id: str | None
    level: str
    kind: str
    title: str
    body: dict
    created_at: str
    read_at: str | None
    quiet_suppressed: int


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    clauses = ["(user_id = ? OR user_id IS NULL)"]
    params = [user["id"]]
    if unread_only:
        clauses.append("read_at IS NULL")
    where = " WHERE " + " AND ".join(clauses)
    rows = db.query(
        f"SELECT * FROM notifications{where} ORDER BY created_at DESC LIMIT ?",
        (*params, limit),
    )
    import json
    result = []
    for r in rows:
        item = dict(r)
        if isinstance(item.get("body"), str):
            try:
                item["body"] = json.loads(item["body"])
            except Exception:
                item["body"] = {}
        result.append(item)
    return result


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    row = db.query_one("SELECT * FROM notifications WHERE id = ? AND (user_id = ? OR user_id IS NULL)", (notification_id, user["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    from app.core.timeutil import iso, utcnow
    db.execute("UPDATE notifications SET read_at = ? WHERE id = ?", (iso(utcnow()), notification_id))
    return {"ok": True}


@router.post("/generate")
def generate_notifications(
    user: dict = Depends(get_current_user),
):
    """Generate notifications for the current user based on alerts, tests, etc."""
    if user["role"] not in {"cmo", "ground", "admin"}:
        raise HTTPException(status_code=403, detail="Only CMO/ground/admin can trigger notification generation")
    from app.notify.engine import generate_all_notifications
    generate_all_notifications(get_db())
    return {"ok": True}