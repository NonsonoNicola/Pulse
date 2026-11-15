from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    idempotency_key TEXT NOT NULL UNIQUE,
    astronaut_id TEXT,
    type TEXT NOT NULL,
    measured_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source TEXT NOT NULL,
    device_id TEXT,
    payload TEXT NOT NULL,
    quality TEXT NOT NULL DEFAULT 'ok',
    quality_reasons TEXT NOT NULL DEFAULT '[]',
    supersedes_id TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1,
    origin_node TEXT NOT NULL DEFAULT 'onboard',
    actor_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_events_measured ON events(astronaut_id, measured_at);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type, measured_at);
CREATE INDEX IF NOT EXISTS idx_events_astronaut ON events(astronaut_id, seq);

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are append-only: corrections require a new event with supersedes_id');
END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are append-only: deletion is not permitted');
END;

CREATE TABLE IF NOT EXISTS crew (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role_title TEXT NOT NULL,
    age INTEGER,
    sex TEXT,
    country TEXT,
    color TEXT,
    allergies TEXT NOT NULL DEFAULT '[]',
    medications TEXT NOT NULL DEFAULT '[]',
    conditions TEXT NOT NULL DEFAULT '[]',
    preflight_baseline TEXT NOT NULL DEFAULT '{}',
    bio TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    astronaut_id TEXT,
    password_hash TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'en',
    explanation_level TEXT NOT NULL DEFAULT 'simple',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor_id TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    detail TEXT NOT NULL DEFAULT '{}',
    emergency_override INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS baselines (
    astronaut_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    center REAL NOT NULL,
    spread REAL NOT NULL,
    n_obs INTEGER NOT NULL,
    origin TEXT NOT NULL,
    frozen INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (astronaut_id, metric)
);

CREATE TABLE IF NOT EXISTS daily_features (
    astronaut_id TEXT NOT NULL,
    date TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    coverage REAL NOT NULL DEFAULT 0,
    quality TEXT NOT NULL DEFAULT 'ok',
    n_obs INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (astronaut_id, date, metric)
);

CREATE TABLE IF NOT EXISTS status_snapshots (
    astronaut_id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    reasons TEXT NOT NULL,
    confidence TEXT NOT NULL,
    coverage REAL NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crew_findings (
    id TEXT PRIMARY KEY,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    metrics TEXT NOT NULL,
    direction TEXT NOT NULL,
    members TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    env_correlations TEXT NOT NULL,
    confidence TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    description_it TEXT NOT NULL DEFAULT '',
    coverage REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    astronaut_id TEXT NOT NULL,
    level TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    protocol_id TEXT,
    opened_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '[]',
    sbar_ids TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    ref_id TEXT,
    priority INTEGER NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT,
    acked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_queue(status, priority, created_at);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    astronaut_id TEXT,
    level TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    read_at TEXT,
    quiet_suppressed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tests (
    id TEXT PRIMARY KEY,
    astronaut_id TEXT NOT NULL,
    date TEXT NOT NULL,
    test TEXT NOT NULL,
    why TEXT NOT NULL,
    minutes INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'suggested',
    completed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    astronaut_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    assessment TEXT,
    sources TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL,
    applies_to TEXT NOT NULL DEFAULT '[]',
    sources TEXT NOT NULL DEFAULT '[]',
    path TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    last_reviewed TEXT
);

CREATE TABLE IF NOT EXISTS kb_chunks (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL,
    section TEXT NOT NULL,
    text TEXT NOT NULL,
    tokens TEXT NOT NULL DEFAULT '[]',
    vector TEXT NOT NULL DEFAULT '[]',
    lang TEXT NOT NULL DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sbars (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    astronaut_id TEXT NOT NULL,
    priority INTEGER NOT NULL,
    payload TEXT NOT NULL,
    markdown TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Database:
    """Small SQLite helper in WAL mode. One connection, guarded by a re-entrant lock."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        with self._lock:
            self._conn.executescript(SCHEMA)

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, tuple(params))

    def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.executemany(sql, rows)

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, tuple(params)).fetchall())

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(sql, tuple(params)).fetchone()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self._lock:
            self._conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def loads(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default
