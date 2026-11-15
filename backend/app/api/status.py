from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user
from app.api.deps import get_analysis
from app.analysis.service import AnalysisService


router = APIRouter(prefix="/astronauts", tags=["status"])


@router.get("/{astronaut_id}/status")
def astronaut_status(
    astronaut_id: str,
    locale: str = Query("en"),
    user: dict = Depends(get_current_user),
    analysis: AnalysisService = Depends(get_analysis),
):
    # Role-based access: astronauts can only see their own, CMO/ground/admin can see all
    if user["role"] == "astronaut" and user.get("astronaut_id") != astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only view their own status")
    bundle = analysis.bundle(locale)
    if astronaut_id not in bundle.snapshots:
        raise HTTPException(status_code=404, detail="Astronaut not found")
    return bundle.snapshot(astronaut_id).status_payload()


@router.get("/{astronaut_id}/booklet")
def astronaut_booklet(
    astronaut_id: str,
    user: dict = Depends(get_current_user),
    analysis: AnalysisService = Depends(get_analysis),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only view their own booklet")
    bundle = analysis.bundle("en")
    if astronaut_id not in bundle.snapshots:
        raise HTTPException(status_code=404, detail="Astronaut not found")
    snap = bundle.snapshot(astronaut_id)
    return {
        "astronaut": {
            "id": snap.astronaut_id,
            "name": snap.name,
            "role_title": snap.role_title,
            "color": snap.color,
        },
        "status": snap.status_payload(),
    }