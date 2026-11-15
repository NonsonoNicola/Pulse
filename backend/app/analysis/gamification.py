from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean
from typing import Any

from app.core.config import load_gamification
from app.core.timeutil import day_key
from app.events.schemas import event_to_out


@dataclass
class GamificationState:
    honesty_days: int
    honesty_days_last_30: int
    time_saved_minutes_7d: int
    daily_ring: dict[str, bool]
    sentinel: dict[str, Any] | None
    crew_goal: dict[str, Any]
    enabled: bool
    disabled_reason: str | None = None


def _parse_day(value: str) -> date:
    return date.fromisoformat(value[:10])


def compute_honesty(events: list[dict[str, Any]], astronaut_id: str, today: date, window_days: int = 90) -> tuple[int, int]:
    honest_days: set[date] = set()
    start = today - timedelta(days=window_days)
    for event in events:
        if event.get("astronaut_id") != astronaut_id:
            continue
        if event.get("type") not in {"checkin", "skipped_checkin"}:
            continue
        try:
            day = _parse_day(event["measured_at"])
        except Exception:
            continue
        if day >= start:
            honest_days.add(day)
    # Backfilled days count as recovered honest days.
    for event in events:
        if event.get("astronaut_id") != astronaut_id:
            continue
        if event.get("type") not in {"checkin", "skipped_checkin", "vital_sample", "sleep_summary"}:
            continue
        try:
            measured = _parse_day(event["measured_at"])
            recorded = _parse_day(event["recorded_at"])
        except Exception:
            continue
        if (recorded - measured).days >= 1 and measured >= start:
            honest_days.add(measured)
    last_30 = len([d for d in honest_days if d >= today - timedelta(days=29)])
    return len(honest_days), last_30


def compute_sentinel(events: list[dict[str, Any]], astronaut_id: str, alert_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    earliest_symptom: dict[str, Any] | None = None
    for event in events:
        if event.get("astronaut_id") != astronaut_id or event.get("type") != "checkin":
            continue
        symptoms = (event.get("payload") or {}).get("symptoms") or []
        if not symptoms:
            continue
        if earliest_symptom is None or event["measured_at"] < earliest_symptom["measured_at"]:
            earliest_symptom = event
    if not earliest_symptom:
        return None
    for alert in sorted(alert_events, key=lambda e: e["measured_at"]):
        if alert.get("astronaut_id") != astronaut_id:
            continue
        if alert["measured_at"] <= earliest_symptom["measured_at"]:
            continue
        lead = (_parse_day(alert["measured_at"]) - _parse_day(earliest_symptom["measured_at"])).days
        if lead >= 1:
            return {
                "awarded": True,
                "lead_days": lead,
                "symptom_event_id": earliest_symptom["id"],
                "alert_event_id": alert["id"],
                "text_en": f"Sentinel: your early report preceded an alert by {lead} day{'s' if lead != 1 else ''}.",
                "text_it": f"Sentinella: la tua segnalazione precoce ha anticipato un allarme di {lead} giorn{'i' if lead != 1 else 'no'}.",
            }
    return None


def compute_gamification(
    events: list[dict[str, Any]],
    astronaut_id: str,
    today: date,
    level: str,
    tests: list[dict[str, Any]],
    completed_tests: list[dict[str, Any]],
    has_checkin_today: bool,
    has_skip_today: bool,
    alert_events: list[dict[str, Any]],
    all_astronaut_ids: list[str],
) -> dict[str, Any]:
    cfg = load_gamification()
    honesty_total, honesty_30 = compute_honesty(events, astronaut_id, today)
    standard = int(cfg.get("time_bank", {}).get("standard_daily_test_minutes", 10))
    week_ago = today - timedelta(days=6)
    completed_minutes = 0
    for test in completed_tests:
        try:
            if _parse_day(test.get("completed_at") or test.get("created_at")) >= week_ago:
                completed_minutes += int(test.get("minutes", 0))
        except Exception:
            continue
    time_saved = max(0, standard * 7 - completed_minutes)
    test_today = tests[0]["test"] if tests else None
    ring = {
        "checkin": has_checkin_today or has_skip_today,
        "test": (not tests) or any(t.get("status") == "completed" for t in tests),
    }

    # Crew participation over the last 7 days, aggregated only.
    participation = 0
    for astronaut in all_astronaut_ids:
        days = set()
        for event in events:
            if event.get("astronaut_id") != astronaut:
                continue
            if event.get("type") not in {"checkin", "skipped_checkin", "vital_sample", "sleep_summary"}:
                continue
            try:
                day = _parse_day(event["measured_at"])
            except Exception:
                continue
            if day >= week_ago:
                days.add(day)
        participation += min(1.0, len(days) / 7.0)
    participation_ratio = participation / max(1, len(all_astronaut_ids))
    target = float(cfg.get("crew_goal", {}).get("weekly_participation_target", 0.8))
    crew_goal = {
        "label_en": "Crew participation this week",
        "label_it": "Partecipazione della crew questa settimana",
        "value": round(participation_ratio, 2),
        "target": target,
        "reached": participation_ratio >= target,
    }

    enabled = level not in {"orange", "red"}
    sentinel = compute_sentinel(events, astronaut_id, alert_events) if cfg.get("sentinel_badge", {}).get("enabled", True) else None
    return {
        "honesty_days": honesty_total,
        "honesty_days_last_30": honesty_30,
        "honesty_note_en": "Reporting and declared skips count. Gaps recovered by backfill count. It never resets.",
        "honesty_note_it": "Contano le segnalazioni e i salti dichiarati. I giorni recuperati col backfill contano. Non si azzera mai.",
        "time_saved_minutes_7d": time_saved,
        "time_saved_note_en": "Fewer unnecessary tests when data are reliable.",
        "time_saved_note_it": "Meno test inutili quando i dati sono affidabili.",
        "daily_ring": ring,
        "test_today": test_today,
        "sentinel": sentinel,
        "crew_goal": crew_goal,
        "enabled": enabled,
        "disabled_reason": None if enabled else "Gamification pauses during orange or red status.",
        "no_leaderboard": True,
    }
