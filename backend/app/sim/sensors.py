from __future__ import annotations

import math
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any, Iterable

import numpy as np

from app.core.timeutil import iso
from app.events.schemas import EventIn
from app.sim.crew import CREW

SEED = 2026
BASE_DAY = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def s1_strength(days_ago: int) -> float:
    if days_ago > 9:
        return 0.0
    return max(0.0, (10 - days_ago) / 10.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _event(
    astronaut_id: str | None,
    type_: str,
    measured: datetime,
    payload: dict[str, Any],
    source: str = "sensor",
    key_suffix: str = "",
    recorded: datetime | None = None,
    device_id: str | None = None,
) -> EventIn:
    stamp = iso(measured)
    return EventIn(
        idempotency_key=f"seed:{astronaut_id or 'env'}:{type_}:{stamp}:{key_suffix}",
        astronaut_id=astronaut_id,
        type=type_,
        measured_at=measured,
        recorded_at=recorded or measured,
        source=source,
        device_id=device_id,
        payload=payload,
        quality=None,
        origin_node="onboard",
    )


def _within_past(measured: datetime, now: datetime) -> bool:
    return measured <= now - timedelta(minutes=6)


def generate_history(now: datetime | None = None, days: int = 60) -> list[EventIn]:
    """Generate 60 days of deterministic synthetic telemetry with S1, S3 gap and S5 fault."""
    now = now or datetime.now(timezone.utc)
    rng = np.random.default_rng(SEED)
    events: list[EventIn] = []
    profiles = {c["id"]: c for c in CREW}
    start = now.date() - timedelta(days=days - 1)

    for offset in range(days):
        day = start + timedelta(days=offset)
        days_ago = (now.date() - day).days
        if days_ago < 0:
            continue
        strength = s1_strength(days_ago)
        gap = days_ago in {1, 2, 3}

        # ---- Environment (3-hour cadence) ----
        for hour in range(0, 24, 3):
            measured = datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)
            if not _within_past(measured, now):
                continue
            co2 = 850 + rng.normal(0, 55) + 1600 * strength
            if days_ago == 0:
                co2 = 2400 + rng.normal(0, 70)
            payload = {
                "co2_ppm": round(_clamp(co2, 500, 4000), 1),
                "cabin_temp_c": round(22.5 + rng.normal(0, 0.35), 1),
                "humidity_pct": round(45 + rng.normal(0, 3), 1),
                "pressure_kpa": round(101.3 + rng.normal(0, 0.2), 2),
                "noise_db": round(58 + rng.normal(0, 3), 1),
                "radiation_usv": round(450 + rng.normal(0, 35), 1),
            }
            events.append(_event(None, "env_sample", measured, payload, source="sensor", key_suffix=f"env{hour}"))

        for profile in CREW:
            crew_id = profile["id"]
            base = profile["baseline"]
            if gap and crew_id == "astronaut_03":
                continue
            s2 = 0.0  # S2 is injected from the scenario lab
            fault = crew_id == "astronaut_04" and days_ago in {0, 1}
            infection_temp = 1.25 * s2
            infection_hr = 13.0 * s2
            sleep_delta = -1.5 * strength - 1.4 * s2
            hrv_factor = 1.0 - 0.24 * strength - 0.22 * s2

            # ---- Vitals (three samples/day) ----
            for index, hour in enumerate((1, 7, 13)):
                measured = datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)
                if not _within_past(measured, now):
                    continue
                resting_hr = base["resting_hr"] + 5.0 * strength + infection_hr + rng.normal(0, 2.0)
                hrv = base["hrv_rmssd"] * hrv_factor + rng.normal(0, 3.0)
                spo2 = base["spo2"] + rng.normal(0, 0.4)
                if fault:
                    spo2 = 86.0 + rng.uniform(0, 3.0)
                skin_temp = base["skin_temp"] + infection_temp + rng.normal(0, 0.12)
                payload = {
                    "resting_hr": round(_clamp(resting_hr, 35, 180), 1),
                    "hrv_rmssd": round(_clamp(hrv, 8, 200), 1),
                    "spo2": round(_clamp(spo2, 70, 100), 1),
                    "skin_temp": round(_clamp(skin_temp, 34, 40), 2),
                    "respiratory_rate": round(_clamp(base["respiratory_rate"] + rng.normal(0, 0.8), 8, 30), 1),
                    "activity_min": round(_clamp(base["activity_min"] + rng.normal(0, 8) - 6 * strength, 5, 150), 0),
                }
                events.append(
                    _event(
                        crew_id,
                        "vital_sample",
                        measured,
                        payload,
                        device_id=f"wearable-{crew_id[-1]}",
                        key_suffix=f"vital{index}",
                    )
                )

            # ---- Sleep summary ----
            sleep_time = datetime.combine(day, time(hour=6, minute=30), tzinfo=timezone.utc)
            if _within_past(sleep_time, now):
                sleep_hours = base["sleep_hours"] + sleep_delta + rng.normal(0, 0.28)
                efficiency = base["sleep_efficiency"] - 9 * strength - 8 * s2 + rng.normal(0, 2.5)
                events.append(
                    _event(
                        crew_id,
                        "sleep_summary",
                        sleep_time,
                        {
                            "sleep_hours": round(_clamp(sleep_hours, 2.5, 11), 2),
                            "sleep_efficiency": round(_clamp(efficiency, 40, 100), 1),
                        },
                        key_suffix="sleep",
                    )
                )

            # ---- Check-in (evening, with some declared skips) ----
            checkin_time = datetime.combine(day, time(hour=20, minute=5), tzinfo=timezone.utc)
            if _within_past(checkin_time, now):
                roll = rng.random()
                if roll < 0.1:
                    events.append(
                        _event(
                            crew_id,
                            "skipped_checkin",
                            checkin_time,
                            {"reason": "no_time", "note": "Long EVA preparation."},
                            source="manual",
                            key_suffix="skip",
                        )
                    )
                elif roll < 0.93:
                    symptoms: list[str] = []
                    if strength > 0.2 and rng.random() < 0.35 + 0.5 * strength:
                        symptoms.append("headache")
                    if strength > 0.5 and rng.random() < 0.35:
                        symptoms.append("fatigue")
                    if strength > 0.7 and rng.random() < 0.25:
                        symptoms.append("insomnia")
                    mood = _clamp(base["mood"] - 0.55 * strength - 0.8 * s2 + rng.normal(0, 0.25), 1, 5)
                    energy = _clamp(base["energy"] - 0.6 * strength - 1.1 * s2 + rng.normal(0, 0.3), 1, 5)
                    payload = {
                        "mood": int(round(mood)),
                        "energy": int(round(energy)),
                        "sleep_quality": int(round(_clamp(4.2 - 1.4 * strength + rng.normal(0, 0.3), 1, 5))),
                        "sleep_hours": round(_clamp(base["sleep_hours"] + sleep_delta + rng.normal(0, 0.3), 2, 12), 2),
                        "symptoms": symptoms,
                        "hydration": int(round(_clamp(base["hydration"] + rng.normal(0, 0.3), 1, 5))),
                        "appetite": int(round(_clamp(4.0 + rng.normal(0, 0.4) - 0.3 * strength, 1, 5))),
                        "pain": {"site": None, "intensity": 0},
                        "note": "Headache again — maybe the air feels stale." if "headache" in symptoms else "",
                    }
                    events.append(
                        _event(crew_id, "checkin", checkin_time, payload, source="manual", key_suffix="checkin")
                    )

        # ---- Weekly manual measurements ----
        if days_ago % 7 == 0:
            for profile in CREW:
                measured = datetime.combine(day, time(hour=9, minute=0), tzinfo=timezone.utc)
                if not _within_past(measured, now):
                    continue
                events.append(
                    _event(
                        profile["id"],
                        "manual_measurement",
                        measured,
                        {
                            "weight_kg": round(72 + rng.normal(0, 0.4), 1),
                            "oral_temp_c": round(36.5 + rng.normal(0, 0.1), 2),
                            "bp_systolic": int(round(118 + rng.normal(0, 4))),
                            "bp_diastolic": int(round(76 + rng.normal(0, 3))),
                        },
                        source="manual",
                        key_suffix="weekly",
                    )
                )

    return events


def generate_infection_burst(astronaut_id: str = "astronaut_02", now: datetime | None = None) -> list[EventIn]:
    """S2: inject four days of fever, higher resting HR and worse sleep for one astronaut."""
    now = now or datetime.now(timezone.utc)
    rng = np.random.default_rng(SEED + 2)
    profile = next(c for c in CREW if c["id"] == astronaut_id)
    base = profile["baseline"]
    events: list[EventIn] = []
    for days_ago in range(4):
        day = now.date() - timedelta(days=days_ago)
        strength = (4 - days_ago) / 4.0
        for index, hour in enumerate((2, 8, 14)):
            measured = datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)
            if days_ago == 0:
                measured = now - timedelta(minutes=30 - index * 5)
            recorded = now
            payload = {
                "resting_hr": round(base["resting_hr"] + 12 + rng.normal(0, 2), 1),
                "hrv_rmssd": round(_clamp(base["hrv_rmssd"] * 0.75 + rng.normal(0, 2), 8, 200), 1),
                "spo2": round(_clamp(base["spo2"] - 0.6 + rng.normal(0, 0.3), 90, 100), 1),
                "skin_temp": round(base["skin_temp"] + 0.9 + 0.35 * strength + rng.normal(0, 0.1), 2),
                "respiratory_rate": round(15 + strength * 2 + rng.normal(0, 0.6), 1),
                "activity_min": round(30 + rng.normal(0, 15), 0),
            }
            events.append(
                _event(
                    astronaut_id,
                    "vital_sample",
                    measured,
                    payload,
                    recorded=recorded,
                    key_suffix=f"s2-vital-{days_ago}-{index}",
                )
            )
        sleep_time = datetime.combine(day, time(hour=6, minute=45), tzinfo=timezone.utc)
        if days_ago == 0:
            sleep_time = now - timedelta(hours=3)
        events.append(
            _event(
                astronaut_id,
                "sleep_summary",
                sleep_time,
                {
                    "sleep_hours": round(5.4 - 0.2 * strength + rng.normal(0, 0.2), 2),
                    "sleep_efficiency": round(72 - 4 * strength + rng.normal(0, 2), 1),
                },
                recorded=now,
                key_suffix=f"s2-sleep-{days_ago}",
            )
        )
        checkin_time = datetime.combine(day, time(hour=20, minute=10), tzinfo=timezone.utc)
        if days_ago == 0:
            checkin_time = now - timedelta(minutes=12)
        events.append(
            _event(
                astronaut_id,
                "checkin",
                checkin_time,
                {
                    "mood": 3,
                    "energy": 2,
                    "sleep_quality": 2,
                    "sleep_hours": 5.4,
                    "symptoms": ["fatigue", "fever_feeling", "headache"],
                    "hydration": 3,
                    "appetite": 2,
                    "pain": {"site": None, "intensity": 0},
                    "note": "Feeling warm and tired. No breath problems.",
                },
                source="manual",
                recorded=now,
                key_suffix=f"s2-checkin-{days_ago}",
            )
        )
    return events


def generate_backfill(astronaut_id: str = "astronaut_03", days_ago_list: Iterable[int] = (1, 2, 3), now: datetime | None = None) -> list[EventIn]:
    """S3: recover the missing days with the original measured_at and a recorded_at of now."""
    now = now or datetime.now(timezone.utc)
    rng = np.random.default_rng(SEED + 3)
    profile = next(c for c in CREW if c["id"] == astronaut_id)
    base = profile["baseline"]
    events: list[EventIn] = []
    for days_ago in days_ago_list:
        day = now.date() - timedelta(days=days_ago)
        strength = s1_strength(days_ago)
        for index, hour in enumerate((1, 7, 13)):
            measured = datetime.combine(day, time(hour=hour), tzinfo=timezone.utc)
            payload = {
                "resting_hr": round(base["resting_hr"] + 5 * strength + rng.normal(0, 2), 1),
                "hrv_rmssd": round(base["hrv_rmssd"] * (1 - 0.24 * strength) + rng.normal(0, 3), 1),
                "spo2": round(base["spo2"] + rng.normal(0, 0.4), 1),
                "skin_temp": round(base["skin_temp"] + rng.normal(0, 0.12), 2),
                "respiratory_rate": 13.0,
                "activity_min": round(base["activity_min"] + rng.normal(0, 6), 0),
            }
            events.append(
                _event(
                    astronaut_id,
                    "vital_sample",
                    measured,
                    payload,
                    recorded=now,
                    key_suffix=f"s3-vital-{days_ago}-{index}",
                )
            )
        events.append(
            _event(
                astronaut_id,
                "sleep_summary",
                datetime.combine(day, time(hour=6, minute=30), tzinfo=timezone.utc),
                {
                    "sleep_hours": round(_clamp(base["sleep_hours"] - 1.4 * strength + rng.normal(0, 0.25), 2.5, 10), 2),
                    "sleep_efficiency": round(base["sleep_efficiency"] - 8 * strength + rng.normal(0, 2), 1),
                },
                recorded=now,
                key_suffix=f"s3-sleep-{days_ago}",
            )
        )
        events.append(
            _event(
                astronaut_id,
                "checkin",
                datetime.combine(day, time(hour=20, minute=5), tzinfo=timezone.utc),
                {
                    "mood": int(round(_clamp(base["mood"] - 0.4 * strength, 1, 5))),
                    "energy": int(round(_clamp(base["energy"] - 0.5 * strength, 1, 5))),
                    "sleep_quality": 3,
                    "sleep_hours": 5.9,
                    "symptoms": ["headache"] if strength > 0.5 else [],
                    "hydration": 4,
                    "appetite": 4,
                    "pain": {"site": None, "intensity": 0},
                    "note": "Backfilled from the wearable after the comms blackout.",
                },
                source="manual",
                recorded=now,
                key_suffix=f"s3-checkin-{days_ago}",
            )
        )
    return events


def generate_fault_check(astronaut_id: str = "astronaut_04", now: datetime | None = None) -> list[EventIn]:
    """S5: add a normal manual re-measurement after the sensor conflict."""
    now = now or datetime.now(timezone.utc)
    return [
        _event(
            astronaut_id,
            "manual_measurement",
            now - timedelta(minutes=2),
            {"spo2": 98.0, "resting_hr": 61, "device_id": "pulse_oximeter_2"},
            source="manual",
            key_suffix="s5-recheck",
        )
    ]
