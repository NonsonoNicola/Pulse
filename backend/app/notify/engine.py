from __future__ import annotations

import json
from datetime import datetime, time
from typing import Any

from app.core.db import Database
from app.core.timeutil import iso, utcnow
from app.events.store import EventStore
from app.analysis.service import AnalysisService
from app.core.config import get_settings, load_gamification


def _in_quiet_hours(now: datetime) -> bool:
    start = 22
    end = 7
    hour = now.hour
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def generate_all_notifications(db: Database) -> int:
    settings = get_settings()
    analysis = AnalysisService(db, settings)
    bundle = analysis.bundle("en")
    now = utcnow()
    created = 0

    # Check each astronaut for alerts
    for snap in bundle.snapshots.values():
        # Level-based notifications
        if snap.level in {"orange", "red"}:
            for user_row in db.query("SELECT id FROM users WHERE role IN ('cmo', 'ground', 'admin') AND active = 1"):
                _create_notification(
                    db,
                    user_id=user_row["id"],
                    astronaut_id=snap.astronaut_id,
                    level=snap.level,
                    kind="alert",
                    title=f"{snap.name}: {snap.level.upper()} status",
                    body={"level": snap.level, "primary_reason": snap.primary_reason},
                    quiet_ok=(snap.level == "red"),
                )
                created += 1

        # Data quality notifications
        if snap.data_quality:
            for user_row in db.query("SELECT id FROM users WHERE role IN ('cmo', 'ground', 'admin') AND active = 1"):
                _create_notification(
                    db,
                    user_id=user_row["id"],
                    astronaut_id=snap.astronaut_id,
                    level="yellow",
                    kind="data_quality",
                    title=f"{snap.name}: Sensor quality issue",
                    body={"flags": snap.data_quality[:3]},
                    quiet_ok=False,
                )
                created += 1

        # Test reminders
        if snap.tests:
            for test in snap.tests:
                if test.get("status") == "suggested":
                    # Notify the astronaut
                    user_row = db.query_one("SELECT id FROM users WHERE astronaut_id = ?", (snap.astronaut_id,))
                    if user_row:
                        _create_notification(
                            db,
                            user_id=user_row["id"],
                            astronaut_id=snap.astronaut_id,
                            level="green",
                            kind="test_reminder",
                            title=f"Suggested test: {test['test'].replace('_', ' ')}",
                            body={"test": test, "why_en": test.get("why_en", ""), "why_it": test.get("why_it", "")},
                            quiet_ok=False,
                        )
                        created += 1

    # Check-in reminders for astronauts who haven't checked in today
    today = now.date()
    for crew_row in db.query("SELECT id FROM crew"):
        astronaut_id = crew_row["id"]
        # Check if there's a checkin or skip today
        events_today = db.query(
            "SELECT 1 FROM events WHERE astronaut_id = ? AND type IN ('checkin', 'skipped_checkin') AND date(measured_at) = ? LIMIT 1",
            (astronaut_id, today.isoformat()),
        )
        if not events_today:
            user_row = db.query_one("SELECT id FROM users WHERE astronaut_id = ?", (astronaut_id,))
            if user_row:
                _create_notification(
                    db,
                    user_id=user_row["id"],
                    astronaut_id=astronaut_id,
                    level="green",
                    kind="checkin_reminder",
                    title="Daily check-in",
                    body={"message": "Time for your daily check-in"},
                    quiet_ok=False,
                )
                created += 1

    # Crew goal notification
    gam = load_gamification()
    if gam.get("crew_goal", {}).get("weekly_participation_target"):
        from app.analysis.gamification import compute_gamification
        for snap in bundle.snapshots.values():
            user_row = db.query_one("SELECT id FROM users WHERE astronaut_id = ?", (snap.astronaut_id,))
            if user_row:
                g = compute_gamification([], snap.astronaut_id, today, snap.level, [], [], False, False, [], list(bundle.snapshots.keys()))
                if g.get("crew_goal", {}).get("reached"):
                    _create_notification(
                        db,
                        user_id=user_row["id"],
                        astronaut_id=snap.astronaut_id,
                        level="green",
                        kind="crew_goal",
                        title="Crew goal reached",
                        body={"goal": "weekly_participation", "value": g["crew_goal"]["value"]},
                        quiet_ok=False,
                    )
                    created += 1

    return created


def _create_notification(
    db: Database,
    user_id: str | None,
    astronaut_id: str | None,
    level: str,
    kind: str,
    title: str,
    body: dict[str, Any],
    quiet_ok: bool = False,
) -> None:
    now = utcnow()
    if not quiet_ok and _in_quiet_hours(now):
        # Suppress but log
        db.execute(
            "INSERT INTO notifications (id, user_id, astronaut_id, level, kind, title, body, created_at, quiet_suppressed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (f"notif:{now.timestamp()}:{user_id or 'broadcast'}", user_id, astronaut_id, level, kind, title, json.dumps(body), iso(now)),
        )
    else:
        db.execute(
            "INSERT INTO notifications (id, user_id, astronaut_id, level, kind, title, body, created_at, quiet_suppressed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (f"notif:{now.timestamp()}:{user_id or 'broadcast'}", user_id, astronaut_id, level, kind, title, json.dumps(body), iso(now)),
        )