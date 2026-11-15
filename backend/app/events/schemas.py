from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.timeutil import iso, parse_iso, utcnow

EVENT_TYPES = {
    "vital_sample",
    "sleep_summary",
    "env_sample",
    "checkin",
    "symptom_report",
    "manual_measurement",
    "skipped_checkin",
    "image_report",
    "voice_report",
    "test_scheduled",
    "test_done",
    "alert",
    "llm_assessment",
    "case_opened",
    "case_note",
    "sbar_packet",
    "ground_message",
    "sync_ack",
    "update_applied",
    "config_change",
    "access_override",
}
SOURCES = {"sensor", "manual", "voice", "image", "derived", "ground", "system"}
QUALITIES = {"ok", "suspect", "invalid", "estimated"}
ORIGINS = {"onboard", "ground"}
LEVELS = {"green", "yellow", "orange", "red", "gray"}


class EventIn(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str | None = None
    astronaut_id: str | None = None
    type: str
    measured_at: datetime = Field(default_factory=utcnow)
    recorded_at: datetime = Field(default_factory=utcnow)
    source: str = "sensor"
    device_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    quality: str | None = None
    quality_reasons: list[str] = Field(default_factory=list)
    supersedes_id: str | None = None
    schema_version: int = 1
    origin_node: str = "onboard"
    actor_id: str | None = None

    @field_validator("type")
    @classmethod
    def _type_ok(cls, value: str) -> str:
        if value not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {value}")
        return value

    @field_validator("source")
    @classmethod
    def _source_ok(cls, value: str) -> str:
        if value not in SOURCES:
            raise ValueError(f"unknown source: {value}")
        return value

    @field_validator("quality")
    @classmethod
    def _quality_ok(cls, value: str | None) -> str | None:
        if value is not None and value not in QUALITIES:
            raise ValueError(f"unknown quality: {value}")
        return value

    @field_validator("origin_node")
    @classmethod
    def _origin_ok(cls, value: str) -> str:
        if value not in ORIGINS:
            raise ValueError(f"unknown origin: {value}")
        return value

    @field_validator("measured_at", "recorded_at")
    @classmethod
    def _tz(cls, value: datetime) -> datetime:
        return parse_iso(value)

    def key(self) -> str:
        if self.idempotency_key:
            return self.idempotency_key
        return f"auto:{self.id}"


class EventOut(BaseModel):
    seq: int
    id: str
    idempotency_key: str
    astronaut_id: str | None
    type: str
    measured_at: str
    recorded_at: str
    source: str
    device_id: str | None
    payload: dict[str, Any]
    quality: str
    quality_reasons: list[str]
    supersedes_id: str | None
    schema_version: int
    origin_node: str
    actor_id: str | None
    created_at: str


class EventBatch(BaseModel):
    events: list[EventIn]


class CheckinIn(BaseModel):
    mood: int | None = None
    energy: int | None = None
    sleep_quality: int | None = None
    sleep_hours: float | None = None
    symptoms: list[str] = Field(default_factory=list)
    pain: dict[str, Any] | None = None
    hydration: int | None = None
    appetite: int | None = None
    note: str | None = None
    unknown_fields: list[str] = Field(default_factory=list)
    voice_only: bool = False
    measured_at: datetime | None = None
    idempotency_key: str | None = None

    @field_validator("mood", "energy", "sleep_quality", "hydration", "appetite")
    @classmethod
    def _scale(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 5:
            raise ValueError("scale answers must be between 1 and 5")
        return value


class SkipIn(BaseModel):
    reason: Literal["blackout", "sensor_issue", "no_time", "other"]
    note: str | None = None
    measured_at: datetime | None = None


def event_to_out(row: Any) -> EventOut:
    return EventOut(
        seq=row["seq"],
        id=row["id"],
        idempotency_key=row["idempotency_key"],
        astronaut_id=row["astronaut_id"],
        type=row["type"],
        measured_at=row["measured_at"],
        recorded_at=row["recorded_at"],
        source=row["source"],
        device_id=row["device_id"],
        payload=json_dict(row["payload"]),
        quality=row["quality"],
        quality_reasons=json_list(row["quality_reasons"]),
        supersedes_id=row["supersedes_id"],
        schema_version=row["schema_version"],
        origin_node=row["origin_node"],
        actor_id=row["actor_id"],
        created_at=row["created_at"],
    )


def json_dict(raw: str) -> dict[str, Any]:
    import json

    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def json_list(raw: str) -> list[str]:
    import json

    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except Exception:
        return []


def normalize_event_dict(event: EventIn) -> dict[str, Any]:
    return {
        "id": event.id,
        "idempotency_key": event.key(),
        "astronaut_id": event.astronaut_id,
        "type": event.type,
        "measured_at": iso(event.measured_at),
        "recorded_at": iso(event.recorded_at),
        "source": event.source,
        "device_id": event.device_id,
        "payload": event.payload,
        "quality": event.quality or "ok",
        "quality_reasons": event.quality_reasons,
        "supersedes_id": event.supersedes_id,
        "schema_version": event.schema_version,
        "origin_node": event.origin_node,
        "actor_id": event.actor_id,
    }
