from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

from app.core.db import Database
from app.core.timeutil import iso, utcnow

PBKDF2_ITERATIONS = 210_000
SESSION_COOKIE = "pulse_session"


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


class Authenticator:
    def __init__(self, db: Database, session_days: int = 30):
        self.db = db
        self.session_days = session_days

    def login(self, username: str, password: str) -> dict[str, Any] | None:
        row = self.db.query_one("SELECT * FROM users WHERE username = ? AND active = 1", (username,))
        if not row:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        token = secrets.token_urlsafe(32)
        now = utcnow()
        self.db.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, row["id"], iso(now), iso(now + timedelta(days=self.session_days))),
        )
        user = dict(row)
        user["token"] = token
        return user

    def user_for_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        row = self.db.query_one(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.expires_at > ? AND u.active = 1",
            (token, iso(utcnow())),
        )
        return dict(row) if row else None

    def logout(self, token: str | None) -> None:
        if token:
            self.db.execute("DELETE FROM sessions WHERE token = ?", (token,))

    @staticmethod
    def public_user(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"],
            "astronaut_id": user.get("astronaut_id"),
            "locale": user.get("locale", "en"),
            "explanation_level": user.get("explanation_level", "simple"),
        }
