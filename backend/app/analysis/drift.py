from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median
from typing import Any

from app.analysis.baseline import Baseline
from app.analysis.features import DayFeature, FEATURE_METRICS

FEATURE_LABELS = {
    "resting_hr": "resting heart rate",
    "hrv_rmssd": "heart-rate variability",
    "spo2": "oxygen saturation",
    "skin_temp": "skin temperature",
    "respiratory_rate": "respiratory rate",
    "sleep_hours": "sleep duration",
    "sleep_efficiency": "sleep efficiency",
    "mood": "mood",
    "energy": "energy",
    "symptom_load": "symptom load",
    "hydration": "hydration",
    "pain": "pain",
    "activity_min": "activity",
}


@dataclass
class Deviation:
    metric: str
    direction: str
    z: float
    recent: float
    center: float
    spread: float
    magnitude: float
    percent: float | None
    n: int
    quality: str
    coverage: float
    baseline_origin: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "direction": self.direction,
            "z": round(self.z, 2),
            "recent": round(self.recent, 2),
            "baseline_center": round(self.center, 2),
            "baseline_spread": round(self.spread, 2),
            "magnitude": round(self.magnitude, 2),
            "percent": round(self.percent, 1) if self.percent is not None else None,
            "n": self.n,
            "quality": self.quality,
            "coverage": self.coverage,
            "baseline_origin": self.baseline_origin,
        }


@dataclass
class Hypothesis:
    id: str
    title: str
    card_id: str
    score: float
    coverage: float
    support: list[str] = field(default_factory=list)
    against: list[str] = field(default_factory=list)
    observed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "card_id": self.card_id,
            "score": round(self.score, 3),
            "coverage": round(self.coverage, 3),
            "support": self.support,
            "against": self.against,
            "observed": self.observed,
        }


def recent_metric(frame: list[DayFeature], metric: str, window: int = 7) -> list[float]:
    values: list[float] = []
    for day in frame[-window:]:
        if metric in day.metrics and day.quality.get(metric) in {"ok", "estimated"}:
            values.append(day.metrics[metric])
    return values


def compute_deviations(frame: list[DayFeature], baselines: dict[str, Baseline], window: int = 7) -> list[Deviation]:
    deviations: list[Deviation] = []
    coverage = round(sum(d.coverage for d in frame[-window:]) / max(1, min(window, len(frame))), 3)
    for metric, baseline in baselines.items():
        if metric not in FEATURE_METRICS and metric not in {"sleep_efficiency"}:
            continue
        values = recent_metric(frame, metric, window)
        if len(values) < 2:
            continue
        recent = median(values)
        z = (recent - baseline.center) / baseline.spread if baseline.spread else 0.0
        pct = ((recent - baseline.center) / baseline.center * 100.0) if baseline.center else None
        qualities = [
            day.quality.get(metric, "ok")
            for day in frame[-window:]
            if metric in day.metrics
        ]
        quality = "suspect" if any(q == "suspect" for q in qualities) else "ok"
        deviations.append(
            Deviation(
                metric=metric,
                direction="above" if z >= 0 else "below",
                z=z,
                recent=recent,
                center=baseline.center,
                spread=baseline.spread,
                magnitude=recent - baseline.center,
                percent=pct,
                n=len(values),
                quality=quality,
                coverage=coverage,
                baseline_origin=baseline.origin,
            )
        )
    return sorted(deviations, key=lambda d: abs(d.z), reverse=True)


def trajectory_vector(frame: list[DayFeature], baselines: dict[str, Baseline], window: int = 7) -> dict[str, float | None]:
    vector: dict[str, float | None] = {}
    for metric in FEATURE_METRICS:
        baseline = baselines.get(metric)
        values = recent_metric(frame, metric, window)
        if not baseline or len(values) < 2:
            vector[metric] = None
            continue
        vector[metric] = (median(values) - baseline.center) / baseline.spread if baseline.spread else 0.0
    return vector


def score_signatures(
    trajectory: dict[str, float | None], signatures: list[dict[str, Any]], top_k: int = 4
) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    for signature in signatures:
        weights: dict[str, float] = signature.get("weights", {})
        weighted_observed = {m: w for m, w in weights.items() if trajectory.get(m) is not None}
        if len(weighted_observed) < 2:
            continue
        z_values = {m: float(trajectory[m]) for m in weighted_observed}
        norm_w = math.sqrt(sum(w * w for w in weighted_observed.values()))
        norm_z = math.sqrt(sum(z * z for z in z_values.values()))
        if norm_w == 0 or norm_z == 0:
            continue
        cosine = sum(weighted_observed[m] * z_values[m] for m in weighted_observed) / (norm_w * norm_z)
        total_weight = sum(abs(w) for w in weights.values()) or 1.0
        coverage = sum(abs(w) for w in weighted_observed.values()) / total_weight
        score = max(0.0, cosine) * (0.5 + 0.5 * coverage)
        support: list[str] = []
        against: list[str] = []
        for metric, z in sorted(z_values.items(), key=lambda item: abs(item[1]), reverse=True):
            aligned = weighted_observed[metric] * z > 0
            label = FEATURE_LABELS.get(metric, metric.replace("_", " "))
            direction = "higher" if z > 0 else "lower"
            text = f"{label} {direction} ({z:+.1f}σ vs baseline)"
            (support if aligned else against).append(text)
        hypotheses.append(
            Hypothesis(
                id=signature["id"],
                title=signature["title"],
                card_id=signature["card_id"],
                score=score,
                coverage=coverage,
                support=support[:3],
                against=against[:2],
                observed=sorted(weighted_observed),
            )
        )
    hypotheses.sort(key=lambda h: h.score, reverse=True)
    return [h for h in hypotheses[:top_k] if h.score > 0.05]


def pattern_description(deviations: list[Deviation], hypotheses: list[Hypothesis], coverage: float) -> str:
    useful = [d for d in deviations if abs(d.z) >= 1.0 and d.quality == "ok"][:5]
    parts = [
        f"{FEATURE_LABELS.get(d.metric, d.metric)} {d.direction} ({d.percent:+.0f}% vs personal baseline, {d.z:+.1f}σ)"
        if d.percent is not None
        else f"{FEATURE_LABELS.get(d.metric, d.metric)} {d.direction} ({d.z:+.1f}σ)"
        for d in useful
    ]
    hypothesis_text = "; ".join(h.title for h in hypotheses[:3])
    return (
        "Astronaut pattern: "
        + ("; ".join(parts) if parts else "no strong deviations")
        + f". Data coverage {coverage:.0%}. Candidate patterns: {hypothesis_text or 'none'}."
    )
