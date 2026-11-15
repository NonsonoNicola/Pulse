from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.deps import get_analysis, get_db, get_event_store
from app.sim.sensors import generate_infection_burst, generate_backfill, generate_fault_check
from app.events.store import EventStore


router = APIRouter(prefix="/demo", tags=["demo"])


class ScenarioIn(BaseModel):
    scenario: str  # S1, S2, S3, S4, S5
    action: str    # inject, backfill, recheck


@router.post("/scenario")
def run_scenario(
    payload: ScenarioIn,
    user: dict = Depends(get_current_user),
    store: EventStore = Depends(get_event_store),
):
    # Demo-only endpoint: the actions are fixed synthetic scenarios (S2, S3 and
    # S5) and never accept arbitrary clinical data. Any authenticated demo user
    # may run them so that ?demo=Sx deep links work for every account.
    # The destructive reset endpoint remains admin-only.

    from app.core.timeutil import utcnow
    now = utcnow()

    events = []
    if payload.scenario == "S2" and payload.action == "inject":
        events = generate_infection_burst("astronaut_02", now)
    elif payload.scenario == "S3" and payload.action == "backfill":
        events = generate_backfill("astronaut_03", [1, 2, 3], now)
    elif payload.scenario == "S5" and payload.action == "recheck":
        events = generate_fault_check("astronaut_04", now)
    else:
        raise HTTPException(status_code=400, detail="Unknown scenario/action")

    store.append_many(events)

    # Update demo state
    import json
    db = get_db()
    row = db.query_one("SELECT value FROM settings WHERE key = 'demo_state'")
    state = json.loads(row["value"]) if row else {"scenarios": {}}
    scenario_state = state["scenarios"].setdefault(payload.scenario, {"active": False})
    scenario_state["active"] = True
    if payload.action == "backfill":
        scenario_state["state"] = "backfilled"
    db.execute("UPDATE settings SET value = ? WHERE key = 'demo_state'", (json.dumps(state),))

    # Invalidate analysis cache
    get_analysis().invalidate()

    return {"injected": len(events), "scenario": payload.scenario, "action": payload.action}


@router.get("/state")
def demo_state(
    user: dict = Depends(get_current_user),
):
    if user["role"] not in {"admin", "ground"}:
        raise HTTPException(status_code=403, detail="Only admin/ground can view demo state")
    db = get_db()
    row = db.query_one("SELECT value FROM settings WHERE key = 'demo_state'")
    if row:
        import json
        return json.loads(row["value"])
    return {"scenarios": {}}


@router.post("/reset")
def demo_reset(
    user: dict = Depends(get_current_user),
):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admin can reset demo")
    from app.sim.seed import seed
    summary = seed(reset=True)
    get_analysis().invalidate()
    return summary