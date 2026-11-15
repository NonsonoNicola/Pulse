from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.analysis.service import AnalysisService
from app.core.config import get_settings, mission_summary
from app.core.db import Database, dumps
from app.core.security import hash_password
from app.core.timeutil import iso, utcnow
from app.events.store import EventStore
from app.sim.crew import CREW, USERS
from app.sim.sensors import generate_history


def reset_data(data_dir: Path) -> None:
    for name in ("crewmd.db", "crewmd.db-wal", "crewmd.db-shm", "ground.db", "ground.db-wal", "ground.db-shm"):
        path = data_dir / name
        if path.exists():
            path.unlink()
    booklet = data_dir / "booklet"
    if booklet.exists():
        shutil.rmtree(booklet, ignore_errors=True)
    booklet.mkdir(parents=True, exist_ok=True)


def seed(reset: bool = False, days: int = 60) -> dict:
    settings = get_settings()
    if reset:
        reset_data(settings.data_dir)
    db = Database(settings.db_path)
    now = utcnow()

    # Profiles
    for profile in CREW:
        db.execute(
            "INSERT OR REPLACE INTO crew "
            "(id, name, role_title, age, sex, country, color, allergies, medications, conditions, preflight_baseline, bio) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                profile["id"],
                profile["name"],
                profile["role_title"],
                profile["age"],
                profile["sex"],
                profile["country"],
                profile["color"],
                dumps(profile["allergies"]),
                dumps(profile["medications"]),
                dumps(profile["conditions"]),
                dumps(profile["preflight_baseline"]),
                profile["bio"],
            ),
        )

    # Accounts
    for user in USERS:
        db.execute(
            "INSERT OR REPLACE INTO users "
            "(id, username, display_name, role, astronaut_id, password_hash, locale, explanation_level, active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                user["id"],
                user["username"],
                user["display_name"],
                user["role"],
                user["astronaut_id"],
                hash_password(user["password"]),
                "en",
                "simple",
                iso(now),
            ),
        )

    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (
            "demo_state",
            dumps(
                {
                    "seeded_at": iso(now),
                    "mission_id": settings.mission_id,
                    "scenarios": {
                        "S1": {"active": True, "label": "Crew CO₂ drift"},
                        "S2": {"active": False, "label": "Single infection"},
                        "S3": {"active": True, "state": "gap", "label": "Blackout + backfill"},
                        "S4": {"active": False, "label": "Emergency in autonomy"},
                        "S5": {"active": True, "label": "Faulty sensor + bias"},
                    },
                }
            ),
        ),
    )
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("mission_id", dumps(settings.mission_id)),
    )

    store = EventStore(db)
    events = generate_history(now=now, days=days)
    store.append_many(events)
    store.audit("system", "demo_seeded", "database", {"events": len(events), "seed": 2026})

    analysis = AnalysisService(db, settings)
    bundle = analysis.bundle("en")
    db.close()
    return {
        "events": len(events),
        "crew": len(CREW),
        "levels": {snapshot.astronaut_id: snapshot.level for snapshot in bundle.snapshots.values()},
        "coverage": {snapshot.astronaut_id: snapshot.coverage for snapshot in bundle.snapshots.values()},
        "findings": len(bundle.crew_findings),
        "database": str(settings.db_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed CrewMD synthetic demo data")
    parser.add_argument("--reset", action="store_true", help="delete the local database and booklet first")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--app-dir", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    summary = seed(reset=args.reset, days=args.days)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
