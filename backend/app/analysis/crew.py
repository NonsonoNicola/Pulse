from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean, median
from typing import Any

import numpy as np

from app.analysis.baseline import Baseline
from app.analysis.features import DayFeature, ENV_METRICS, FEATURE_METRICS
from app.analysis.drift import FEATURE_LABELS
from app.core.config import load_thresholds
from app.core.timeutil import day_key

ENV_LABELS = {
    "co2_ppm": ("cabin CO₂", "CO₂ in cabina"),
    "cabin_temp_c": ("cabin temperature", "temperatura in cabina"),
    "noise_db": ("noise level", "livello di rumore"),
    "radiation_usv": ("radiation dose", "dose di radiazioni"),
    "humidity_pct": ("humidity", "umidità"),
}

CREW_METRICS = [
    "sleep_hours",
    "hrv_rmssd",
    "resting_hr",
    "symptom_load",
    "skin_temp",
    "spo2",
    "mood",
    "energy",
]

FEATURE_LABELS_IT = {
    "resting_hr": "frequenza cardiaca a riposo",
    "hrv_rmssd": "variabilità cardiaca",
    "spo2": "saturazione di ossigeno",
    "skin_temp": "temperatura cutanea",
    "respiratory_rate": "frequenza respiratoria",
    "sleep_hours": "durata del sonno",
    "sleep_efficiency": "efficienza del sonno",
    "mood": "umore",
    "energy": "energia",
    "symptom_load": "carico di sintomi",
    "hydration": "idratazione",
    "pain": "dolore",
    "activity_min": "attività",
}


def _join(items: list[str], locale: str) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    conjunction = " e " if locale == "it" else " and "
    return ", ".join(items[:-1]) + conjunction + items[-1]


@dataclass
class EnvCorrelation:
    env_metric: str
    r: float
    p_value: float
    lag_days: int
    n: int
    confidence: str
    significant: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "env_metric": self.env_metric,
            "r": round(self.r, 3),
            "p_value": round(self.p_value, 4),
            "lag_days": self.lag_days,
            "n": self.n,
            "confidence": self.confidence,
            "significant": self.significant,
            "note": "Correlation is not causation.",
        }


@dataclass
class CrewFinding:
    id: str
    window_start: str
    window_end: str
    metrics: list[dict[str, Any]]
    direction: str
    members: list[dict[str, Any]]
    member_count: int
    env_correlations: list[dict[str, Any]]
    confidence: str
    status: str
    description_en: str
    description_it: str
    coverage: float

    def as_dict(self, hide_ids: bool = True) -> dict[str, Any]:
        return {
            "id": self.id,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "metrics": self.metrics,
            "direction": self.direction,
            "members": [] if hide_ids else self.members,
            "member_count": self.member_count,
            "env_correlations": self.env_correlations,
            "confidence": self.confidence,
            "status": self.status,
            "description_en": self.description_en,
            "description_it": self.description_it,
            "coverage": self.coverage,
            "not_causation": True,
        }


def _mean_z(
    frames: dict[str, list[DayFeature]], baselines: dict[str, dict[str, Baseline]], metric: str, astronaut_id: str
) -> float | None:
    base = baselines.get(astronaut_id, {}).get(metric)
    frame = frames.get(astronaut_id, [])
    if not base or len(frame) < 2:
        return None
    values = [
        day.metrics[metric]
        for day in frame[-7:]
        if metric in day.metrics and day.quality.get(metric) in {"ok", "estimated"}
    ]
    if len(values) < 2:
        return None
    return (median(values) - base.center) / base.spread if base.spread else 0.0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 4:
        return None
    mx, my = mean(xs), mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-12 or vy <= 1e-12:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def _crew_metric_series(
    frames: dict[str, list[DayFeature]], baselines: dict[str, dict[str, Baseline]], metric: str, days: int
) -> dict[str, float]:
    end = max((frame[-1].date for frame in frames.values() if frame), default=date.today())
    series: dict[str, list[float]] = {}
    for astronaut_id, frame in frames.items():
        base = baselines.get(astronaut_id, {}).get(metric)
        if not base or not base.spread:
            continue
        for day in frame[-days:]:
            if metric in day.metrics and day.quality.get(metric) in {"ok", "estimated"}:
                z = (day.metrics[metric] - base.center) / base.spread
                series.setdefault(day.date.isoformat(), []).append(z)
    return {key: mean(values) for key, values in series.items()}


def _env_series(env_frame: list[dict[str, Any]], metric: str, days: int) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in env_frame[-days:]:
        if metric in row.get("metrics", {}):
            out[row["date"]] = row["metrics"][metric]
    return out


def _correlate(
    crew_series: dict[str, float],
    env_series: dict[str, float],
    metric: str,
    lags: list[int],
    permutations: int,
    min_abs_r: float,
    max_p: float,
) -> EnvCorrelation | None:
    best: tuple[float, int, float, int, list[float], list[float]] | None = None
    for lag in lags:
        pairs: list[tuple[float, float]] = []
        for key, crew_value in crew_series.items():
            try:
                # Positive lag means the environment changed that many days *before* the crew shift.
                env_date = (date.fromisoformat(key) - timedelta(days=lag)).isoformat()
            except ValueError:
                continue
            if env_date in env_series:
                pairs.append((env_series[env_date], crew_value))
        if len(pairs) < 8:
            continue
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        r = _pearson(xs, ys)
        if r is None:
            continue
        # Penalise long lags slightly: with short, smoothly trending windows the peak is
        # often broad, and a smaller lag is easier to interpret and to act on.
        score = abs(r) - 0.03 * abs(lag)
        if best is None or score > abs(best[0]) - 0.03 * abs(best[1]):
            best = (r, lag, 0.0, len(pairs), xs, ys)

    if best is None:
        return None
    r, lag, _, n, xs, ys = best
    rng = np.random.default_rng(abs(hash((metric, lag, n))) % (2**32))
    y_arr = np.array(ys)
    extreme = 0
    for _ in range(permutations):
        shuffled = rng.permutation(y_arr)
        rp = np.corrcoef(np.array(xs), shuffled)[0, 1] if np.std(shuffled) > 0 else 0.0
        if abs(float(rp)) >= abs(r):
            extreme += 1
    p_value = (extreme + 1) / (permutations + 1)
    significant = abs(r) >= min_abs_r and p_value <= max_p
    if abs(r) >= 0.65 and p_value <= 0.05:
        confidence = "high"
    elif significant:
        confidence = "medium"
    else:
        confidence = "low"
    return EnvCorrelation(
        env_metric=metric,
        r=r,
        p_value=p_value,
        lag_days=lag,
        n=n,
        confidence=confidence,
        significant=significant,
    )


def compute_crew_findings(
    frames: dict[str, list[DayFeature]],
    baselines: dict[str, dict[str, Baseline]],
    env_frame: list[dict[str, Any]],
    locale: str = "en",
) -> list[CrewFinding]:
    thresholds = load_thresholds().get("crew", {})
    z_threshold = float(thresholds.get("deviation_z_threshold", 1.5))
    min_members = int(thresholds.get("min_members", 2))
    window = int(thresholds.get("correlation_window_days", 30))
    lags = [int(x) for x in thresholds.get("lags_days", [-3, -2, -1, 0, 1, 2, 3])]
    permutations = int(thresholds.get("permutations", 300))
    min_abs_r = float(thresholds.get("min_abs_r", 0.4))
    max_p = float(thresholds.get("max_p_value", 0.1))

    candidates: list[tuple[str, list[dict[str, Any]], str, float]] = []
    for metric in CREW_METRICS:
        members: list[dict[str, Any]] = []
        for astronaut_id in frames:
            z = _mean_z(frames, baselines, metric, astronaut_id)
            if z is not None and abs(z) >= z_threshold:
                members.append({"astronaut_id": astronaut_id, "z": round(z, 2)})
        if len(members) < min_members:
            continue
        below = [m for m in members if m["z"] < 0]
        above = [m for m in members if m["z"] > 0]
        dominant = "below" if len(below) >= len(above) else "above"
        same = below if dominant == "below" else above
        if len(same) < min_members:
            continue
        effect = mean(abs(m["z"]) for m in same)
        candidates.append(
            (
                metric,
                [{**m, "direction": "below" if m["z"] < 0 else "above"} for m in same],
                dominant,
                effect,
            )
        )

    if not candidates:
        return []

    # One finding per window. Keep the strongest metrics so the crew view stays legible.
    candidates.sort(key=lambda item: item[3], reverse=True)
    chosen = candidates[:4]
    primary_metric, primary_members, primary_direction, _ = chosen[0]
    window_end = max((frame[-1].date for frame in frames.values() if frame), default=date.today())
    window_start = window_end - timedelta(days=6)
    coverage = round(
        mean(
            [
                mean([day.coverage for day in frame[-7:]])
                for frame in frames.values()
                if frame
            ]
        ),
        3,
    )

    crew_series = _crew_metric_series(frames, baselines, primary_metric, window)
    correlations: list[dict[str, Any]] = []
    for env_metric in ENV_METRICS:
        env_series = _env_series(env_frame, env_metric, window)
        corr = _correlate(
            crew_series,
            env_series,
            env_metric,
            lags,
            permutations,
            min_abs_r,
            max_p,
        )
        if corr:
            correlations.append(corr.as_dict())
    correlations.sort(key=lambda c: (not c["significant"], -abs(c["r"])))

    member_map: dict[str, dict[str, Any]] = {}
    for metric, members, direction, effect in chosen:
        for member in members:
            entry = member_map.setdefault(
                member["astronaut_id"], {"astronaut_id": member["astronaut_id"], "z_by_metric": {}}
            )
            entry["z_by_metric"][metric] = member["z"]
    member_count = len(member_map)
    confidence = "high" if member_count >= 3 and coverage >= 0.6 else "medium" if coverage >= 0.4 else "low"
    if not any(c["significant"] for c in correlations) and confidence == "high":
        confidence = "medium"

    below_en = [FEATURE_LABELS.get(m, m.replace("_", " ")) for m, _, d, _ in chosen if d == "below"]
    below_it = [FEATURE_LABELS_IT.get(m, m.replace("_", " ")) for m, _, d, _ in chosen if d == "below"]
    above_en = [FEATURE_LABELS.get(m, m.replace("_", " ")) for m, _, d, _ in chosen if d == "above"]
    above_it = [FEATURE_LABELS_IT.get(m, m.replace("_", " ")) for m, _, d, _ in chosen if d == "above"]
    env_clause_en = ""
    env_clause_it = ""
    significant = [c for c in correlations if c["significant"]]
    if significant:
        top = significant[0]
        label_en, label_it = ENV_LABELS.get(top["env_metric"], (top["env_metric"], top["env_metric"]))
        lag = top["lag_days"]
        if lag == 0:
            lag_en, lag_it = "same day", "stesso giorno"
        elif lag > 0:
            lag_en, lag_it = f"{lag} days earlier", f"{lag} giorni prima"
        else:
            lag_en, lag_it = f"{abs(lag)} days later", f"{abs(lag)} giorni dopo"
        env_clause_en = (
            f" {label_en[0].upper() + label_en[1:]} moved with this shift (r = {top['r']:+.2f}, {lag_en}, n = {top['n']})."
        )
        env_clause_it = (
            f" {label_it[0].upper() + label_it[1:]} si è mossa con questo cambiamento (r = {top['r']:+.2f}, {lag_it}, n = {top['n']})."
        )

    parts_en: list[str] = []
    if below_en:
        parts_en.append(f"{_join(below_en, 'en')} moved lower")
    if above_en:
        parts_en.append(f"{_join(above_en, 'en')} moved higher")
    parts_it: list[str] = []
    if below_it:
        parts_it.append(f"{_join(below_it, 'it')} in calo")
    if above_it:
        parts_it.append(f"{_join(above_it, 'it')} in aumento")
    description_en = (
        f"{member_count} of {len(frames)} crew members show a coordinated shift over the last 7 days: "
        + " and ".join(parts_en)
        + "."
        + env_clause_en
        + " A shared environmental exposure is plausible; this is not a diagnosis."
    )
    description_it = (
        f"{member_count} astronauti su {len(frames)} mostrano uno spostamento coordinato negli ultimi 7 giorni: "
        + " e ".join(parts_it)
        + "."
        + env_clause_it
        + " È plausibile un'esposizione ambientale condivisa; non è una diagnosi."
    )

    finding = CrewFinding(
        id=f"cf_{window_end.isoformat()}_{primary_direction}",
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        metrics=[
            {
                "metric": metric,
                "direction": direction,
                "mean_z": round(effect, 2),
                "members": len(members),
            }
            for metric, members, direction, effect in chosen
        ],
        direction=primary_direction,
        members=list(member_map.values()),
        member_count=member_count,
        env_correlations=correlations,
        confidence=confidence,
        status="open",
        description_en=description_en,
        description_it=description_it,
        coverage=coverage,
    )
    return [finding]
