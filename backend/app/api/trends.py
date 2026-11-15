from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user
from app.api.deps import get_analysis
from app.analysis.service import AnalysisService


router = APIRouter(prefix="/astronauts", tags=["trends"])


@router.get("/{astronaut_id}/trends")
def astronaut_trends(
    astronaut_id: str,
    days: int = Query(30, ge=1, le=180),
    locale: str = Query("en"),
    user: dict = Depends(get_current_user),
    analysis: AnalysisService = Depends(get_analysis),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only view their own trends")
    return analysis.trends(astronaut_id, days, locale)


@router.get("/environment/trends")
def environment_trends(
    days: int = Query(30, ge=1, le=180),
    user: dict = Depends(get_current_user),
    analysis: AnalysisService = Depends(get_analysis),
):
    if user["role"] == "astronaut":
        raise HTTPException(status_code=403, detail="Astronauts cannot view environment trends")
    return analysis.environment_trends(days)