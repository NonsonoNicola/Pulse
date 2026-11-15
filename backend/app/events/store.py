from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Iterable

from app.analysis.quality import assess_event_quality, extract_metrics, recent_metric_window
from app.core.db import Database, dumps, loads
from app.core.timeutil import iso, parse_iso, utcnow
from app.events.schemas import EventIn, event_to_out, normalize_event_dict


class EventStore:
    """Append-only event store. Idempotency is enforced by a unique key."""

    def __init__(self, db: Database):
        self.db = db

    def append(self, event: EventIn, actor_id: str | None = None) -> tuple[dict[str, Any], bool]:
        if event.quality is None:
            recent_rows = self.db.query(
                "SELECT astronaut_id, measured_at, payload FROM events "
                "WHERE astronaut_id IS ? ORDER BY measured_at DESC, seq DESC LIMIT 40",
                (event.astronaut_id,),
            )
            recent = recent_metric_window([dict(r) for r in recent_rows], event.astronaut_id, event.measured_at)
            quality, reasons = assess_event_quality(event, recent)
            event.quality = quality
            event.quality_reasons = reasons
        data = normalize_event_dict(event)
        if actor_id:
            data["actor_id"] = actor_id
        _insert(self.db, data)
        row = self.db.query_one("SELECT * FROM events WHERE idempotency_key = ?", (data["idempotency_key"],))
        return event_to_out(row).model_dump(), row["id"] == data["id"]

    def append_many(self, events: Iterable[EventIn], actor_id: str | None = None) -> list[tuple[dict[str, Any], bool]]:
        payloads: list[dict[str, Any]] = []
        recent_cache: dict[str, list[dict[str, Any]]] = {}
        for event in sorted(events, key=lambda e: e.measured_at):
            key = event.astronaut_id or "__env__"
            if key not in recent_cache:
                rows = self.db.query(
                    "SELECT astronaut_id, measured_at, payload FROM events "
                    "WHERE astronaut_id IS ? ORDER BY measured_at DESC, seq DESC LIMIT 40",
                    (event.astronaut_id,),
                )
                recent_cache[key] = recent_metric_window(
                    [dict(r) for r in rows], event.astronaut_id, event.measured_at
                )
            if event.quality is None:
                quality, reasons = assess_event_quality(event, recent_cache[key])
                event.quality = quality
                event.quality_reasons = reasons
            data = normalize_event_dict(event)
            if actor_id:
                data["actor_id"] = actor_id
            payloads.append(data)
            metrics = extract_metrics(event.payload)
            if metrics:
                recent_cache[key].append({"metrics": metrics, "measured_at": iso(event.measured_at)})
                recent_cache[key] = recent_cache[key][-8:]

        created: list[tuple[dict[str, Any], bool]] = []
        with self.db.transaction() as conn:
            for data in payloads:
                before = conn.total_changes
                _insert(self.db, data)
                made = conn.total_changes > before
                created.append((data, made))
        out: list[tuple[dict[str, Any], bool]] = []
        for data, made in created:
            row = self.db.query_one("SELECT * FROM events WHERE idempotency_key = ?", (data["idempotency_key"],))
            out.append((event_to_out(row).model_dump(), made and row["id"] == data["id"]))
        return out

    def append_system(
        self,
        type_: str,
        payload: dict[str, Any],
        astronaut_id: str | None = None,
        measured_at: datetime | None = None,
        source: str = "system",
        actor_id: str | None = None,
        origin_node: str = "onboard",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        event = EventIn(
            idempotency_key=idempotency_key or f"{type_}:{uuid.uuid4()}",
            astronaut_id=astronaut_id,
            type=type_,
            measured_at=measured_at or utcnow(),
            source=source,
            payload=payload,
            quality="ok",
            origin_node=origin_node,
        )
        record, _ = self.append(event, actor_id=actor_id)
        return record

    def get(self, event_id: str) -> dict[str, Any] | None:
        row = self.db.query_one("SELECT * FROM events WHERE id = ?", (event_id,))
        return event_to_out(row).model_dump() if row else None

    def list(
        self,
        astronaut_id: str | None = None,
        types: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if astronaut_id is not None:
            clauses.append("astronaut_id = ?")
            params.append(astronaut_id)
        if types:
            clauses.append(f"type IN ({','.join('?' for _ in types)})")
            params.extend(types)
        if start:
            clauses.append("measured_at >= ?")
            params.append(iso(start))
        if end:
            clauses.append("measured_at <= ?")
            params.append(iso(end))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        order = "ASC" if ascending else "DESC"
        rows = self.db.query(
            f"SELECT * FROM events{where} ORDER BY measured_at {order}, seq {order} LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        return [event_to_out(row).model_dump() for row in rows]

    def all_for(self, astronaut_id: str) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT * FROM events WHERE astronaut_id = ? ORDER BY measured_at ASC, seq ASC", (astronaut_id,)
        )
        return [dict(r) for r in rows]

    def latest(self, types: list[str] | None = None, limit: int = 20, astronaut_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if types:
            clauses.append(f"type IN ({','.join('?' for _ in types)})")
            params.extend(types)
        if astronaut_id:
            clauses.append("astronaut_id = ?")
            params.append(astronaut_id)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.db.query(
            f"SELECT * FROM events{where} ORDER BY measured_at DESC, seq DESC LIMIT ?", (*params, limit)
        )
        return [event_to_out(row).model_dump() for row in rows]

    def count(self) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS n FROM events")
        return int(row["n"]) if row else 0

    def count_by_type(self) -> dict[str, int]:
        rows = self.db.query("SELECT type, COUNT(*) AS n FROM events GROUP BY type")
        return {r["type"]: int(r["n"]) for r in rows}

    def audit(
        self,
        actor_id: str | None,
        action: str,
        resource: str | None = None,
        detail: dict[str, Any] | None = None,
        emergency_override: bool = False,
    ) -> None:
        self.db.execute(
            "INSERT INTO audit_log (at, actor_id, action, resource, detail, emergency_override) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (iso(utcnow()), actor_id, action, resource, dumps(detail or {}), 1 if emergency_override else 0),
        )


def _insert(db: Database, data: dict[str, Any]) -> None:
    db.execute(
        "INSERT OR IGNORE INTO events "
        "(id, idempotency_key, astronaut_id, type, measured_at, recorded_at, source, device_id, payload, "
        " quality, quality_reasons, supersedes_id, schema_version, origin_node, actor_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data["id"],
            data["idempotency_key"],
            data["astronaut_id"],
            data["type"],
            data["measured_at"],
            data["recorded_at"],
            data["source"],
            data["device_id"],
            dumps(data["payload"]),
            data["quality"],
            dumps(data["quality_reasons"]),
            data["supersedes_id"],
            data["schema_version"],
            data["origin_node"],
            data.get("actor_id"),
        ),
    )
