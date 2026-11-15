from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.api.deps import get_db, get_llm_service
from app.llm.service import LLMService


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatIn(BaseModel):
    astronaut_id: str
    message: str
    locale: str = "en"
    explanation_level: str = "simple"
    forced_protocol: str | None = None
    emergency: bool = False
    case_id: str | None = None


class ChatOut(BaseModel):
    assessment: dict
    markdown: str
    mode: str
    model: str | None
    emergency: bool
    case_id: str | None


@router.post("", response_model=ChatOut)
def chat(
    payload: ChatIn,
    user: dict = Depends(get_current_user),
    llm: LLMService = Depends(get_llm_service),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != payload.astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only chat about themselves")
    result = llm.chat(
        user=user,
        astronaut_id=payload.astronaut_id,
        message=payload.message,
        locale=payload.locale,
        explanation_level=payload.explanation_level,
        forced_protocol=payload.forced_protocol,
        emergency=payload.emergency,
        case_id=payload.case_id,
    )
    return ChatOut(
        assessment=result.assessment.model_dump(),
        markdown=result.markdown,
        mode=result.mode,
        model=result.model,
        emergency=result.emergency,
        case_id=result.case_id,
    )


@router.post("/stream")
def chat_stream(
    payload: ChatIn,
    user: dict = Depends(get_current_user),
    llm: LLMService = Depends(get_llm_service),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != payload.astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only chat about themselves")

    async def generate() -> AsyncGenerator[str, None]:
        result = llm.chat(
            user=user,
            astronaut_id=payload.astronaut_id,
            message=payload.message,
            locale=payload.locale,
            explanation_level=payload.explanation_level,
            forced_protocol=payload.forced_protocol,
            emergency=payload.emergency,
            case_id=payload.case_id,
        )
        # Stream the markdown in chunks
        for i in range(0, len(result.markdown), 100):
            chunk = result.markdown[i : i + 100]
            yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'assessment': result.assessment.model_dump()})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history/{astronaut_id}")
def chat_history(
    astronaut_id: str,
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    if user["role"] == "astronaut" and user.get("astronaut_id") != astronaut_id:
        raise HTTPException(status_code=403, detail="Astronauts can only view their own chat history")
    rows = db.query(
        "SELECT * FROM chat_messages WHERE astronaut_id = ? ORDER BY created_at DESC LIMIT ?",
        (astronaut_id, limit),
    )
    return [dict(r) for r in rows]