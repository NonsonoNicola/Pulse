from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.config import load_thresholds
from app.core.timeutil import parse_iso, utcnow
from app.events.schemas import EventIn

# Payload keys that carry a single scalar health/environment measure.
METRIC_KEYS = {
    "resting_hr",
    "hrv_rmssd",
    "spo2",
    "skin_temp",
    "respiratory_rate",
    "sleep_hours",
    "sleep_efficiency",
    "mood",
    "energy",
    "hydration",
    "pain_score",
    "activity_min",
    "co2_ppm",
    "cabin_temp_c",
    "humidity_pct",
    "pressure_kpa",
    "noise_db",
    "radiation_usv",
}


def extract_metrics(payload: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    for key in METRIC_KEYS:
        raw = payload.get(key)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            values[key] = float(raw)
    pain = payload.get("pain")
    if isinstance(pain, dict) and isinstance(pain.get("intensity"), (int, float)):
        values["pain_score"] = float(pain["intensity"])
    return values


def assess_event_quality(event: EventIn, recent: list[dict[str, Any]] | None = None) -> tuple[str, list[str]]:
    """Deterministic data-quality assessment. Returns worst quality plus human-readable reasons."""
    thresholds = load_thresholds()
    plausible = thresholds.get("quality", {}).get("plausible", {})
    reasons: list[str] = []
    quality = event.quality or "ok"

    now = utcnow()
    if event.measured_at > now + timedelta(minutes=thresholds.get("quality", {}).get("future_tolerance_minutes", 5)):
        return "invalid", ["future_timestamp"]

    metrics = extract_metrics(event.payload)
    for metric, value in metrics.items():
        bounds = plausible.get(metric)
        if bounds and not (bounds[0] <= value <= bounds[1]):
            reasons.append(f"implausible_{metric}")
            quality = "invalid"

    if quality != "invalid":
        flatline_window = int(thresholds.get("quality", {}).get("flatline_window", 3))
        if recent and metrics:
            for metric, value in metrics.items():
                same = 0
                for previous in reversed(recent):
                    if metric in previous["metrics"] and previous["metrics"][metric] == value:
                        same += 1
                    else:
                        break
                if same + 1 >= flatline_window:
                    reasons.append(f"flatline_{metric}")
                    if quality == "ok":
                        quality = "suspect"

        spo2_rule = thresholds.get("quality", {}).get("spo2_discordance", {})
        if spo2_rule.get("enabled") and "spo2" in metrics:
            spo2 = metrics["spo2"]
            hr = metrics.get("resting_hr") or metrics.get("heart_rate")
            rr = metrics.get("respiratory_rate")
            hr_ok = hr is None or spo2_rule["hr_normal"][0] <= hr <= spo2_rule["hr_normal"][1]
            rr_ok = rr is None or spo2_rule["respiratory_rate_normal"][0] <= rr <= spo2_rule["respiratory_rate_normal"][1]
            if spo2 < spo2_rule["spo2_below"] and hr_ok and rr_ok:
                reasons.append("spo2_discordant_with_hr_rr")
                if quality == "ok":
                    quality = "suspect"

    return quality, sorted(set(reasons))


def recent_metric_window(
    events: list[dict[str, Any]], astronaut_id: str | None, before, max_events: int = 6
) -> list[dict[str, Any]]:
    relevant: list[dict[str, Any]] = []
    for event in reversed(events):
        if event.get("astronaut_id") != astronaut_id:
            continue
        payload = event.get("payload")
        if isinstance(payload, str):
            import json
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        metrics = extract_metrics(payload or {})
        if not metrics:
            continue
        if before is not None and parse_iso(event["measured_at"]) > before:
            continue
        relevant.append({"metrics": metrics, "measured_at": event["measured_at"]})
        if len(relevant) >= max_events:
            break
    return list(reversed(relevant))
