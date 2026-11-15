from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import median
from typing import Any, Iterable

from app.analysis.quality import extract_metrics
from app.core.config import load_thresholds
from app.core.timeutil import date_range, day_key, iso, parse_iso, utcnow

FEATURE_METRICS = [
    "resting_hr",
    "hrv_rmssd",
    "spo2",
    "skin_temp",
    "respiratory_rate",
    "sleep_hours",
    "sleep_efficiency",
    "mood",
    "energy",
    "symptom_load",
    "hydration",
    "pain",
    "activity_min",
]

VITAL_METRICS = {"resting_hr", "hrv_rmssd", "spo2", "skin_temp", "respiratory_rate", "activity_min"}
SLEEP_METRICS = {"sleep_hours", "sleep_efficiency"}
CHECKIN_METRICS = {"mood", "energy", "hydration"}
ENV_METRICS = {"co2_ppm", "cabin_temp_c", "humidity_pct", "pressure_kpa", "noise_db", "radiation_usv"}

SYMPTOM_WEIGHTS = {
    "headache": 1.0,
    "nausea": 1.2,
    "dizziness": 1.2,
    "fatigue": 1.0,
    "insomnia": 1.0,
    "poor_appetite": 0.7,
    "abdominal_pain": 1.2,
    "congestion": 0.6,
    "sore_throat": 0.6,
    "cough": 0.8,
    "shortness_of_breath": 3.0,
    "chest_pain": 3.0,
    "palpitations": 1.5,
    "back_pain": 1.0,
    "joint_pain": 1.0,
    "rash": 0.8,
    "wound": 1.0,
    "fever_feeling": 1.2,
    "dehydration": 1.0,
    "anxiety": 1.0,
    "low_mood": 0.8,
}


@dataclass
class DayFeature:
    date: date
    metrics: dict[str, float] = field(default_factory=dict)
    quality: dict[str, str] = field(default_factory=dict)
    coverage: float = 0.0
    n_obs: int = 0
    has_checkin: bool = False
    has_skip: bool = False
    backfilled: bool = False
    vital_samples: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "metrics": self.metrics,
            "quality": self.quality,
            "coverage": round(self.coverage, 3),
            "n_obs": self.n_obs,
            "has_checkin": self.has_checkin,
            "has_skip": self.has_skip,
            "backfilled": self.backfilled,
        }


def _worst_quality(qualities: list[str]) -> str:
    order = ["ok", "estimated", "suspect", "invalid"]
    return max(qualities, key=lambda q: order.index(q) if q in order else 0)


def _symptom_load(payload: dict[str, Any]) -> float:
    symptoms = payload.get("symptoms") or []
    load = sum(SYMPTOM_WEIGHTS.get(str(s), 1.0) for s in symptoms)
    pain = payload.get("pain")
    if isinstance(pain, dict) and isinstance(pain.get("intensity"), (int, float)):
        load += float(pain["intensity"]) / 5.0
    return round(load, 2)


def build_daily_features(
    events: Iterable[dict[str, Any]],
    end: date,
    days: int = 60,
    astronaut_id: str | None = None,
) -> list[DayFeature]:
    thresholds = load_thresholds()
    start = end - timedelta(days=days - 1)
    # For each day and metric, track all observations and the latest by recorded_at
    buckets: dict[str, dict[str, list[tuple[float, str, str]]]] = {}  # (value, quality, recorded_at)
    meta: dict[str, dict[str, Any]] = {
        d.isoformat(): {
            "vital": 0,
            "sleep": False,
            "checkin": False,
            "skip": False,
            "backfilled": False,
            "n_obs": 0,
        }
        for d in date_range(start, end)
    }

    for event in events:
        if astronaut_id is not None and event.get("astronaut_id") != astronaut_id:
            continue
        if event.get("astronaut_id") is None:
            continue
        try:
            measured = parse_iso(event["measured_at"])
        except Exception:
            continue
        key = measured.date().isoformat()
        if key not in meta:
            continue
        payload = event.get("payload") or {}
        quality = event.get("quality", "ok")
        recorded_at = event.get("recorded_at", event["measured_at"])
        state = meta[key]
        state["n_obs"] += 1
        try:
            lag = parse_iso(recorded_at) - measured
            if lag > timedelta(hours=6):
                state["backfilled"] = True
        except Exception:
            pass
        values = extract_metrics(payload)
        if event["type"] == "vital_sample":
            state["vital"] += 1
            values = {k: v for k, v in values.items() if k in VITAL_METRICS}
        elif event["type"] == "sleep_summary":
            state["sleep"] = True
            values = {k: v for k, v in values.items() if k in SLEEP_METRICS}
        elif event["type"] == "checkin":
            state["checkin"] = True
            values = {k: v for k, v in values.items() if k in CHECKIN_METRICS}
            if "symptoms" in payload:
                values["symptom_load"] = _symptom_load(payload)
            pain = payload.get("pain")
            if isinstance(pain, dict) and isinstance(pain.get("intensity"), (int, float)):
                values["pain"] = float(pain["intensity"])
        elif event["type"] == "symptom_report":
            if "symptoms" in payload:
                values["symptom_load"] = _symptom_load(payload)
        elif event["type"] == "skipped_checkin":
            state["skip"] = True
            continue
        elif event["type"] in {"manual_measurement", "test_done"}:
            if "oral_temp_c" in payload:
                values["skin_temp"] = float(payload["oral_temp_c"])
        else:
            continue

        for metric, value in values.items():
            buckets.setdefault(key, {}).setdefault(metric, []).append((float(value), quality, recorded_at))

    features: list[DayFeature] = []
    expected = float(thresholds.get("coverage", {}).get("expected_signals_per_day", 5))
    for d in date_range(start, end):
        key = d.isoformat()
        state = meta[key]
        feature = DayFeature(
            date=d,
            coverage=min(1.0, (min(state["vital"], 3) + int(state["sleep"]) + int(state["checkin"] or state["skip"])) / expected),
            n_obs=state["n_obs"],
            has_checkin=state["checkin"],
            has_skip=state["skip"],
            backfilled=state["backfilled"],
            vital_samples=state["vital"],
        )
        for metric, observations in buckets.get(key, {}).items():
            valid = [(v, q, r) for v, q, r in observations if q != "invalid"]
            if not valid:
                feature.quality[metric] = "invalid"
                continue
            # Use the most recently recorded value (by recorded_at) as the primary value.
            # This ensures that backfilled/corrected measurements (recorded later) take precedence.
            valid.sort(key=lambda x: x[2], reverse=True)
            feature.metrics[metric] = round(valid[0][0], 3)
            feature.quality[metric] = _worst_quality([q for _, q, _ in valid])
        features.append(feature)
    return features


def env_daily_features(events: Iterable[dict[str, Any]], end: date, days: int = 60) -> list[dict[str, Any]]:
    start = end - timedelta(days=days - 1)
    buckets: dict[str, dict[str, list[float]]] = {}
    counts: dict[str, int] = {}
    for event in events:
        if event.get("type") != "env_sample":
            continue
        try:
            measured = parse_iso(event["measured_at"])
        except Exception:
            continue
        key = measured.date().isoformat()
        if not (start.isoformat() <= key <= end.isoformat()):
            continue
        counts[key] = counts.get(key, 0) + 1
        for metric, value in extract_metrics(event.get("payload") or {}).items():
            if metric in ENV_METRICS:
                buckets.setdefault(key, {}).setdefault(metric, []).append(float(value))
    out: list[dict[str, Any]] = []
    for d in date_range(start, end):
        key = d.isoformat()
        metrics = {m: round(median(vals), 3) for m, vals in buckets.get(key, {}).items() if vals}
        out.append(
            {
                "date": key,
                "metrics": metrics,
                "coverage": min(1.0, counts.get(key, 0) / 8.0),
                "n_obs": counts.get(key, 0),
            }
        )
    return out


def recent_values(frame: list[DayFeature], metric: str, window: int, include_today: bool = True) -> list[tuple[date, float, str]]:
    subset = frame[-window:] if include_today else frame[-window - 1 : -1]
    out: list[tuple[date, float, str]] = []
    for day in subset:
        if metric in day.metrics:
            out.append((day.date, day.metrics[metric], day.quality.get(metric, "ok")))
    return out


def coverage_recent(frame: list[DayFeature], window: int = 3) -> float:
    if not frame:
        return 0.0
    subset = frame[-window:]
    return round(sum(d.coverage for d in subset) / len(subset), 3)


def metric_trajectory(frame: list[DayFeature], metric: str, window: int = 7) -> float | None:
    values = [v for _, v, q in recent_values(frame, metric, window) if q in {"ok", "estimated"}]
    if len(values) < 2:
        return None
    return median(values)


def build_env_lookup(env_frame: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    return {row["date"]: row["metrics"] for row in env_frame}


def frame_window(frame: list[DayFeature], days: int) -> list[DayFeature]:
    return frame[-days:] if days > 0 else frame


def frame_to_rows(frame: list[DayFeature], astronaut_id: str) -> list[dict[str, Any]]:
    rows = []
    for day in frame:
        for metric, value in day.metrics.items():
            rows.append(
                {
                    "astronaut_id": astronaut_id,
                    "date": day.date.isoformat(),
                    "metric": metric,
                    "value": value,
                    "coverage": day.coverage,
                    "quality": day.quality.get(metric, "ok"),
                    "n_obs": day.n_obs,
                }
            )
    return rows


def observed_at_now() -> str:
    return iso(utcnow())
