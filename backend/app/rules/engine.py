from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any

from app.analysis.baseline import Baseline
from app.analysis.features import DayFeature
from app.core.config import load_critical_phrases, load_symptoms, load_thresholds
from app.core.timeutil import parse_iso

LEVEL_ORDER = {"gray": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4}


def max_level(levels: list[str]) -> str:
    if not levels:
        return "green"
    return max(levels, key=lambda level: LEVEL_ORDER.get(level, 0))


@dataclass
class RuleHit:
    rule_id: str
    level: str
    scope: str
    astronaut_id: str | None
    metric: str | None
    value: float | None
    threshold: float | None
    days: int
    explanation: str
    protocol: str | None
    card_id: str | None
    kind: str
    value_text: str = ""
    threshold_text: str = ""
    quality: str = "ok"
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "level": self.level,
            "scope": self.scope,
            "astronaut_id": self.astronaut_id,
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "value_text": self.value_text,
            "days": self.days,
            "explanation": self.explanation,
            "protocol": self.protocol,
            "card_id": self.card_id,
            "kind": self.kind,
            "quality": self.quality,
            "evidence": self.evidence,
        }


def _level_for(value: float, thresholds: dict[str, float], direction: str) -> str | None:
    result: str | None = None
    for level in ("yellow", "orange", "red"):
        threshold = thresholds.get(level)
        if threshold is None:
            continue
        if direction == "below" and value < threshold:
            result = level
        elif direction == "above" and value > threshold:
            result = level
    return result


def _threshold_for(value: float, thresholds: dict[str, float], direction: str) -> float | None:
    selected: float | None = None
    for level in ("yellow", "orange", "red"):
        threshold = thresholds.get(level)
        if threshold is None:
            continue
        if direction == "below" and value < threshold:
            selected = threshold
        elif direction == "above" and value > threshold:
            selected = threshold
    return selected


def _unit(metric: str | None) -> str:
    if not metric:
        return ""
    population = load_thresholds().get("population_ranges", {}).get(metric, {})
    return str(population.get("unit", ""))


def _fmt(value: float, metric: str | None) -> str:
    unit = _unit(metric)
    decimals = 0 if abs(value) >= 20 else 1
    text = f"{value:.{decimals}f}"
    return f"{text} {unit}".strip()


def _series(frame: list[DayFeature], metric: str, window: int) -> tuple[list[float], int]:
    values = [
        day.metrics[metric]
        for day in frame[-window:]
        if metric in day.metrics and day.quality.get(metric) in {"ok", "estimated"}
    ]
    days = sum(1 for day in frame[-window:] if metric in day.metrics)
    return values, days


def evaluate_rules(
    rules: list[dict[str, Any]],
    frames: dict[str, list[DayFeature]],
    baselines: dict[str, dict[str, Baseline]],
    env_frame: list[dict[str, Any]],
    events: list[dict[str, Any]],
    locale: str = "en",
) -> list[RuleHit]:
    hits: list[RuleHit] = []
    symptoms_cfg = load_symptoms().get("critical_symptoms", {})
    phrases_cfg = load_critical_phrases().get("phrases", [])

    for rule in rules:
        if not rule.get("enabled", True):
            continue
        kind = rule.get("kind", "metric")
        explain = rule.get("explain", {})
        text = explain.get(locale) or explain.get("en") or rule.get("id", "")

        if kind == "metric":
            metric = rule["metric"]
            window = int(rule.get("persistence_days", 3))
            for astronaut_id, frame in frames.items():
                if len(frame) < 2:
                    continue
                values, days_with_data = _series(frame, metric, window)
                min_obs = int(rule.get("min_observations", 2))
                if len(values) < min_obs:
                    continue
                recent = median(values)
                baseline = baselines.get(astronaut_id, {}).get(metric)
                mode = rule.get("mode", "absolute")
                if mode == "absolute":
                    measured = recent
                elif mode == "deviation" and baseline:
                    measured = recent - baseline.center
                elif mode == "percent_deviation" and baseline and baseline.center:
                    measured = (recent - baseline.center) / baseline.center * 100.0
                else:
                    continue
                direction = rule.get("direction", "above")
                level = _level_for(measured, rule.get("thresholds", {}), direction)
                if not level:
                    continue
                threshold = _threshold_for(measured, rule.get("thresholds", {}), direction)
                if mode == "deviation":
                    value_text = _fmt(abs(measured), metric)
                    threshold_text = _fmt(abs(threshold or 0.0), metric)
                elif mode == "percent_deviation":
                    value_text = f"{abs(measured):.0f}%"
                    threshold_text = f"{abs(threshold or 0.0):.0f}%"
                else:
                    value_text = _fmt(recent, metric)
                    threshold_text = _fmt(threshold or 0.0, metric)
                explanation = text.format(
                    value=value_text.replace("+", ""),
                    threshold=threshold_text.replace("+", ""),
                    days=window,
                    metric=metric.replace("_", " "),
                )
                hits.append(
                    RuleHit(
                        rule_id=rule["id"],
                        level=level,
                        scope="astronaut",
                        astronaut_id=astronaut_id,
                        metric=metric,
                        value=round(measured, 3),
                        threshold=threshold,
                        days=window,
                        explanation=explanation,
                        protocol=rule.get("protocol"),
                        card_id=rule.get("card_id"),
                        kind=kind,
                        value_text=value_text,
                        threshold_text=threshold_text,
                        quality="ok",
                    )
                )

        elif kind == "environment":
            metric = rule["metric"]
            window = int(rule.get("persistence_days", 3))
            values = [
                day["metrics"][metric]
                for day in env_frame[-window:]
                if metric in day.get("metrics", {})
            ]
            if len(values) < int(rule.get("min_observations", 2)):
                continue
            recent = median(values)
            level = _level_for(recent, rule.get("thresholds", {}), rule.get("direction", "above"))
            if not level:
                continue
            threshold = _threshold_for(recent, rule.get("thresholds", {}), rule.get("direction", "above"))
            value_text = _fmt(recent, metric)
            threshold_text = _fmt(threshold or 0.0, metric)
            explanation = text.format(
                value=value_text.replace("+", ""),
                threshold=threshold_text.replace("+", ""),
                days=window,
                metric=metric.replace("_", " "),
            )
            hits.append(
                RuleHit(
                    rule_id=rule["id"],
                    level=level,
                    scope="crew_environment",
                    astronaut_id=None,
                    metric=metric,
                    value=round(recent, 3),
                    threshold=threshold,
                    days=window,
                    explanation=explanation,
                    protocol=rule.get("protocol"),
                    card_id=rule.get("card_id"),
                    kind=kind,
                    value_text=value_text,
                    threshold_text=threshold_text,
                )
            )

        elif kind == "critical_symptom":
            for astronaut_id, frame in frames.items():
                for event in _recent_events(events, astronaut_id, hours=48):
                    if event.get("type") not in {"checkin", "symptom_report"}:
                        continue
                    present = (event.get("payload") or {}).get("symptoms") or []
                    for symptom_id in present:
                        crit = symptoms_cfg.get(symptom_id)
                        if not crit:
                            continue
                        label = crit.get(f"label_{locale}") or crit.get("label_en") or symptom_id.replace("_", " ")
                        hits.append(
                            RuleHit(
                                rule_id=f"{rule['id']}:{symptom_id}",
                                level=crit.get("level", "red"),
                                scope="astronaut",
                                astronaut_id=astronaut_id,
                                metric=None,
                                value=None,
                                threshold=None,
                                days=1,
                                explanation=text.format(symptom=label, days=1, value="", threshold=""),
                                protocol=crit.get("protocol"),
                                card_id=rule.get("card_id"),
                                kind=kind,
                                evidence=[{"event_id": event["id"], "type": event["type"], "at": event["measured_at"]}],
                            )
                        )

        elif kind == "critical_phrase":
            for astronaut_id, frame in frames.items():
                for event in _recent_events(events, astronaut_id, hours=48):
                    if event.get("type") not in {"checkin", "symptom_report", "voice_report", "case_note"}:
                        continue
                    payload = event.get("payload") or {}
                    text_blob = " ".join(
                        str(payload.get(key, "")) for key in ("note", "text", "transcript", "message")
                    ).lower()
                    if not text_blob:
                        continue
                    for phrase in phrases_cfg:
                        matched = any(p.lower() in text_blob for p in phrase.get("en", []) + phrase.get("it", []))
                        if not matched:
                            continue
                        label = phrase.get(f"label_{locale}") or phrase.get("label_en") or phrase["id"]
                        hits.append(
                            RuleHit(
                                rule_id=f"{rule['id']}:{phrase['id']}",
                                level=phrase.get("level", "red"),
                                scope="astronaut",
                                astronaut_id=astronaut_id,
                                metric=None,
                                value=None,
                                threshold=None,
                                days=1,
                                explanation=text.format(symptom=label, days=1, value="", threshold=""),
                                protocol=phrase.get("protocol"),
                                card_id=rule.get("card_id"),
                                kind=kind,
                                evidence=[{"event_id": event["id"], "type": event["type"], "at": event["measured_at"]}],
                            )
                        )

        elif kind == "sensor_quality":
            lookback = int(rule.get("lookback_days", 2))
            metrics = rule.get("metrics", [])
            for astronaut_id, frame in frames.items():
                suspect = [
                    metric
                    for metric in metrics
                    for day in frame[-lookback:]
                    if day.quality.get(metric) == "suspect"
                ]
                if not suspect:
                    continue
                hits.append(
                    RuleHit(
                        rule_id=rule["id"],
                        level=rule.get("level", "yellow"),
                        scope="astronaut",
                        astronaut_id=astronaut_id,
                        metric=suspect[0],
                        value=None,
                        threshold=None,
                        days=lookback,
                        explanation=text,
                        protocol=rule.get("protocol"),
                        card_id=rule.get("card_id"),
                        kind=kind,
                        quality="suspect",
                    )
                )
    return hits


def _recent_events(events: list[dict[str, Any]], astronaut_id: str, hours: int) -> list[dict[str, Any]]:
    from app.core.timeutil import utcnow

    cutoff = utcnow().timestamp() - hours * 3600
    out = []
    for event in reversed(events):
        if event.get("astronaut_id") != astronaut_id:
            continue
        try:
            if parse_iso(event["measured_at"]).timestamp() < cutoff:
                continue
        except Exception:
            continue
        out.append(event)
    return out
