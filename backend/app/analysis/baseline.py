from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any

from app.analysis.features import DayFeature
from app.core.config import load_thresholds


@dataclass
class Baseline:
    metric: str
    center: float
    spread: float
    n_obs: int
    origin: str  # personal | population
    frozen: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "center": round(self.center, 3),
            "spread": round(self.spread, 3),
            "n_obs": self.n_obs,
            "origin": self.origin,
            "frozen": self.frozen,
        }


def _mad(values: list[float], center: float) -> float:
    return median([abs(v - center) for v in values]) if values else 0.0


def compute_baselines(frame: list[DayFeature], frozen_metrics: set[str] | None = None) -> dict[str, Baseline]:
    """Gap-aware personal baselines. Recent days are excluded so slow drift does not become normal."""
    thresholds = load_thresholds()
    cfg = thresholds.get("baseline", {})
    reference_days = int(cfg.get("reference_days", 50))
    exclude_recent = int(cfg.get("exclude_recent_days", 10))
    min_obs = int(cfg.get("min_observations", 10))
    mad_scale = float(cfg.get("mad_scale", 1.4826))
    min_spread = cfg.get("min_spread", {})
    population = thresholds.get("population_ranges", {})
    frozen = frozen_metrics or set()

    training = frame[:-exclude_recent] if len(frame) > exclude_recent else []
    training = training[-reference_days:]
    baselines: dict[str, Baseline] = {}

    metrics = sorted({m for day in frame for m in day.metrics})
    for metric in metrics:
        values = [
            day.metrics[metric]
            for day in training
            if metric in day.metrics and day.quality.get(metric) == "ok"
        ]
        if len(values) >= min_obs:
            center = median(values)
            spread = max(mad_scale * _mad(values, center), float(min_spread.get(metric, 0.01)))
            baselines[metric] = Baseline(
                metric=metric,
                center=center,
                spread=spread,
                n_obs=len(values),
                origin="personal",
                frozen=metric in frozen,
            )
        else:
            pop = population.get(metric)
            if pop:
                baselines[metric] = Baseline(
                    metric=metric,
                    center=float(pop["center"]),
                    spread=float(pop["spread"]),
                    n_obs=len(values),
                    origin="population",
                    frozen=False,
                )
    return baselines


def baseline_rows(astronaut_id: str, baselines: dict[str, Baseline], timestamp: str) -> list[tuple[Any, ...]]:
    return [
        (
            astronaut_id,
            b.metric,
            round(b.center, 4),
            round(b.spread, 4),
            b.n_obs,
            b.origin,
            1 if b.frozen else 0,
            1,
            timestamp,
        )
        for b in baselines.values()
    ]
