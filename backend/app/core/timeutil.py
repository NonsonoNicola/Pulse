from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Iterator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def day_key(value: datetime | date | str) -> str:
    if isinstance(value, str):
        return parse_iso(value).date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def day_start_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)


def days_ago(n: int) -> datetime:
    return utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - _timedelta_days(n)


def _timedelta_days(n: int):
    from datetime import timedelta

    return timedelta(days=n)


def date_range(start: date, end: date) -> Iterator[date]:
    from datetime import timedelta

    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def human_duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 90:
        return f"{seconds} s"
    minutes = seconds // 60
    if minutes < 90:
        return f"{minutes} min"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} h"
    return f"{hours // 24} days"
