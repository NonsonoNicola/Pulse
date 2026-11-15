from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user
from app.api.deps import get_analysis
from app.analysis.service import AnalysisService


router = APIRouter(prefix="/crew", tags=["crew"])


@router.get("/summary")
def crew_summary(
    locale: str = Query("en"),
    user: dict = Depends(get_current_user),
    analysis: AnalysisService = Depends(get_analysis),
):
    if user["role"] == "astronaut":
        raise HTTPException(status_code=403, detail="Astronauts cannot view crew summary")
    bundle = analysis.bundle(locale)
    return bundle.crew_summary(locale)


@router.get("/members")
def crew_members(
    user: dict = Depends(get_current_user),
    analysis: AnalysisService = Depends(get_analysis),
):
    if user["role"] == "astronaut":
        raise HTTPException(status_code=403, detail="Astronauts cannot view crew members")
    return analysis.crew()