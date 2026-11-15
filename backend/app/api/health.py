from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_llm_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health(llm = Depends(get_llm_service)):
    return {
        "status": "ok",
        "service": "pulse",
        "llm": llm.status(),
    }