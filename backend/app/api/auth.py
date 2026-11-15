from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import get_db
from app.core.security import Authenticator
from app.core.config import get_settings


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    user: dict
    token: str


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    astronaut_id: str | None
    locale: str
    explanation_level: str


class PreferencesIn(BaseModel):
    locale: str | None = None
    explanation_level: str | None = None


def get_authenticator() -> Authenticator:
    return Authenticator(get_db())


@router.post("/login", response_model=LoginOut)
def login(
    payload: LoginIn,
    response: Response,
    authenticator: Authenticator = Depends(get_authenticator),
):
    user = authenticator.login(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    response.set_cookie(
        key="crewmd_session",
        value=user["token"],
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/",
    )
    return LoginOut(user=Authenticator.public_user(user), token=user["token"])


@router.post("/logout")
def logout(response: Response, token: str | None = Cookie(None, alias="crewmd_session")):
    if token:
        auth = Authenticator(get_db())
        auth.logout(token)
    response.delete_cookie("crewmd_session", path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(
    token: str | None = Cookie(None, alias="crewmd_session"),
    authenticator: Authenticator = Depends(get_authenticator),
):
    user = authenticator.user_for_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return Authenticator.public_user(user)


@router.get("/mission")
def mission():
    from app.core.config import mission_summary, get_settings
    s = get_settings()
    return mission_summary(s.mission_id)


# Shared dependency for protected routes
def get_current_user(
    token: str | None = Cookie(None, alias="crewmd_session"),
    authenticator: Authenticator = Depends(get_authenticator),
):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = authenticator.user_for_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


@router.patch("/me/preferences", response_model=UserOut)
def update_preferences(
    payload: PreferencesIn,
    user: dict = Depends(get_current_user),
):
    if payload.locale is not None and payload.locale not in {"en", "it"}:
        raise HTTPException(status_code=422, detail="locale must be 'en' or 'it'")
    if payload.explanation_level is not None and payload.explanation_level not in {
        "simple",
        "detailed",
        "clinical",
    }:
        raise HTTPException(
            status_code=422,
            detail="explanation_level must be simple, detailed or clinical",
        )
    db = get_db()
    updates = []
    params: list[str] = []
    if payload.locale is not None:
        updates.append("locale = ?")
        params.append(payload.locale)
    if payload.explanation_level is not None:
        updates.append("explanation_level = ?")
        params.append(payload.explanation_level)
    if updates:
        params.append(user["id"])
        db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
    row = db.query_one("SELECT * FROM users WHERE id = ?", (user["id"],))
    return Authenticator.public_user(dict(row) if row else user)