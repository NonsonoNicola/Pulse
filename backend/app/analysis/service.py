from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from app.analysis.baseline import Baseline, baseline_rows, compute_baselines
from app.analysis.crew import CrewFinding, compute_crew_findings
from app.analysis.drift import (
    Deviation,
    Hypothesis,
    compute_deviations,
    pattern_description,
    score_signatures,
    trajectory_vector,
)
from app.analysis.features import (
    FEATURE_METRICS,
    DayFeature,
    build_daily_features,
    build_env_lookup,
    coverage_recent,
    env_daily_features,
    frame_to_rows,
)
from app.analysis.gamification import compute_gamification
from app.analysis.scheduling import suggest_tests
from app.core.config import (
    load_rules,
    load_signatures,
    load_thresholds,
    mission_summary,
)
from app.core.db import Database, dumps, loads
from app.core.timeutil import day_key, iso, parse_iso, utcnow
from app.events.schemas import event_to_out
from app.rules.engine import RuleHit, evaluate_rules, max_level


@dataclass
class AstronautSnapshot:
    astronaut_id: str
    name: str
    role_title: str
    color: str
    level: str
    confidence: str
    confidence_reasons: list[str]
    coverage: float
    reasons: list[dict[str, Any]]
    primary_reason: str
    frame: list[DayFeature]
    baselines: dict[str, Baseline]
    deviations: list[Deviation]
    hypotheses: list[Hypothesis]
    crew_findings: list[CrewFinding]
    environmental_alerts: list[RuleHit]
    data_quality: list[dict[str, Any]]
    tests: list[dict[str, Any]]
    gamification: dict[str, Any]
    computed_at: str
    backfilled_recent: bool
    pattern_description: str

    def status_payload(self) -> dict[str, Any]:
        return {
            "astronaut_id": self.astronaut_id,
            "name": self.name,
            "role_title": self.role_title,
            "color": self.color,
            "level": self.level,
            "confidence": self.confidence,
            "confidence_reasons": self.confidence_reasons,
            "coverage": self.coverage,
            "reasons": self.reasons,
            "primary_reason": self.primary_reason,
            "computed_at": self.computed_at,
            "backfilled_recent": self.backfilled_recent,
            "data_quality": self.data_quality,
            "environmental_alerts": [hit.as_dict() for hit in self.environmental_alerts],
            "gamification": self.gamification,
            "tests": self.tests,
            "hypotheses": [h.as_dict() for h in self.hypotheses],
            "deviations": [d.as_dict() for d in self.deviations[:8]],
            "baselines": {metric: b.as_dict() for metric, b in self.baselines.items()},
        }


@dataclass
class AnalysisBundle:
    snapshots: dict[str, AstronautSnapshot]
    crew_findings: list[CrewFinding]
    environmental_alerts: list[RuleHit]
    env_frame: list[dict[str, Any]]
    crew: list[dict[str, Any]]
    events: list[dict[str, Any]]
    computed_at: str
    locale: str

    def snapshot(self, astronaut_id: str) -> AstronautSnapshot:
        if astronaut_id not in self.snapshots:
            raise KeyError(f"unknown astronaut: {astronaut_id}")
        return self.snapshots[astronaut_id]

    def crew_summary(self, locale: str = "en") -> dict[str, Any]:
        counts = {"green": 0, "yellow": 0, "orange": 0, "red": 0, "gray": 0}
        for snapshot in self.snapshots.values():
            counts[snapshot.level] = counts.get(snapshot.level, 0) + 1
        any_snapshot = next(iter(self.snapshots.values()))
        return {
            "level_counts": counts,
            "member_count": len(self.snapshots),
            "coverage": round(mean([s.coverage for s in self.snapshots.values()]), 3) if self.snapshots else 0,
            "findings": [f.as_dict() for f in self.crew_findings],
            "environmental_alerts": [hit.as_dict() for hit in self.environmental_alerts],
            "crew_goal": any_snapshot.gamification.get("crew_goal") if any_snapshot else None,
            "computed_at": self.computed_at,
            "note_en": "Crew view shows aggregates and shared environment only, never another astronaut's individual data.",
            "note_it": "La vista crew mostra solo aggregati e ambiente condiviso, mai i dati individuali di altri astronauti.",
        }


class AnalysisService:
    def __init__(self, db: Database, settings: Any):
        self.db = db
        self.settings = settings
        self._cache: dict[str, tuple[float, AnalysisBundle]] = {}
        self._cache_ttl_s = 4.0

    def invalidate(self) -> None:
        self._cache.clear()

    def crew(self) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM crew ORDER BY rowid ASC")
        return [dict(row) for row in rows]

    def bundle(self, locale: str = "en") -> AnalysisBundle:
        cached = self._cache.get(locale)
        if cached and time.time() - cached[0] < self._cache_ttl_s:
            return cached[1]
        bundle = self._compute(locale)
        self._cache[locale] = (time.time(), bundle)
        return bundle

    def _compute(self, locale: str) -> AnalysisBundle:
        now = utcnow()
        today = now.date()
        events = [
            event_to_out(row).model_dump()
            for row in self.db.query("SELECT * FROM events ORDER BY measured_at ASC, seq ASC")
        ]
        crew_rows = self.crew()
        crew_ids = [row["id"] for row in crew_rows]
        frames = {crew_id: build_daily_features(events, end=today, days=60, astronaut_id=crew_id) for crew_id in crew_ids}
        env_frame = env_daily_features(events, end=today, days=60)
        env_lookup = build_env_lookup(env_frame)

        previous = {
            row["astronaut_id"]: dict(row)
            for row in self.db.query("SELECT * FROM status_snapshots")
        }
        thresholds = load_thresholds()
        freeze_levels = set(thresholds.get("baseline", {}).get("freeze_levels", []))
        baselines: dict[str, dict[str, Baseline]] = {}
        frozen_metrics: dict[str, set[str]] = {}
        for crew_id in crew_ids:
            frozen: set[str] = set()
            previous_status = previous.get(crew_id, {}).get("level")
            if previous_status in freeze_levels:
                stored = self.db.query("SELECT * FROM baselines WHERE astronaut_id = ?", (crew_id,))
                frozen = {row["metric"] for row in stored}
            frozen_metrics[crew_id] = frozen
            computed = compute_baselines(frames[crew_id], frozen_metrics=frozen)
            if frozen:
                stored_rows = {
                    row["metric"]: dict(row)
                    for row in self.db.query("SELECT * FROM baselines WHERE astronaut_id = ?", (crew_id,))
                }
                for metric, stored in stored_rows.items():
                    if metric in computed:
                        computed[metric] = Baseline(
                            metric=metric,
                            center=stored["center"],
                            spread=stored["spread"],
                            n_obs=stored["n_obs"],
                            origin=stored["origin"],
                            frozen=True,
                        )
            baselines[crew_id] = computed

        deviations = {
            crew_id: compute_deviations(frames[crew_id], baselines[crew_id]) for crew_id in crew_ids
        }
        hypotheses = {
            crew_id: score_signatures(
                trajectory_vector(frames[crew_id], baselines[crew_id]), load_signatures()
            )
            for crew_id in crew_ids
        }
        descriptions = {
            crew_id: pattern_description(deviations[crew_id], hypotheses[crew_id], coverage_recent(frames[crew_id]))
            for crew_id in crew_ids
        }
        rules = load_rules()
        hits = evaluate_rules(rules, frames, baselines, env_frame, events, locale=locale)
        crew_findings = compute_crew_findings(frames, baselines, env_frame, locale=locale)
        environmental_hits = [hit for hit in hits if hit.scope == "crew_environment"]

        snapshots: dict[str, AstronautSnapshot] = {}
        for crew_row in crew_rows:
            crew_id = crew_row["id"]
            personal_hits = sorted(
                [hit for hit in hits if hit.scope == "astronaut" and hit.astronaut_id == crew_id],
                key=lambda hit: ({"gray": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4}.get(hit.level, 0)),
                reverse=True,
            )
            frame = frames[crew_id]
            coverage = coverage_recent(frame, 3)
            data_quality = self._quality_snapshot(events, crew_id)
            confidence, confidence_reasons = self._confidence(
                personal_hits, coverage, data_quality, baselines[crew_id]
            )
            reasons = [hit.as_dict() for hit in personal_hits]
            missing_days = sum(1 for day in frame[-2:] if day.coverage == 0)
            if coverage < float(thresholds.get("coverage", {}).get("min_confidence_coverage", 0.4)):
                reasons.append(
                    {
                        "rule_id": "data_gap",
                        "level": "gray",
                        "scope": "data",
                        "kind": "data_gap",
                        "days": missing_days,
                        "explanation": (
                            "Not enough recent data to assess you. Recover the missing days or check in when you can."
                            if locale == "en"
                            else "Non ci sono dati recenti sufficienti per valutarti. Recupera i giorni mancanti o fai il check-in quando puoi."
                        ),
                        "protocol": None,
                        "card_id": None,
                        "value": None,
                        "threshold": None,
                        "evidence": [],
                    }
                )
            level = max_level([hit.level for hit in personal_hits])
            if not personal_hits and coverage < float(
                thresholds.get("coverage", {}).get("min_confidence_coverage", 0.4)
            ):
                level = "gray"
            primary = self._primary_reason(level, reasons, locale)
            backfilled = any(day.backfilled for day in frame[-3:])
            # Gray means "not enough data to assess", so do not suggest clinical tests from a stale
            # state; offer only the baseline refresh path once fresh data arrive.
            tests = (
                []
                if level == "gray"
                else self._ensure_tests(
                    crew_id, today, deviations[crew_id], baselines[crew_id], data_quality, coverage
                )
            )
            completed = self._recent_tests(crew_id, today)
            has_checkin = frame[-1].has_checkin if frame else False
            has_skip = frame[-1].has_skip if frame else False
            gamification = compute_gamification(
                events,
                crew_id,
                today,
                level,
                tests,
                completed + tests,
                has_checkin,
                has_skip,
                [e for e in events if e["type"] in {"alert", "case_opened"}],
                crew_ids,
            )
            snapshots[crew_id] = AstronautSnapshot(
                astronaut_id=crew_id,
                name=crew_row["name"],
                role_title=crew_row.get("role_title", ""),
                color=crew_row.get("color", "#5eead4"),
                level=level,
                confidence=confidence,
                confidence_reasons=confidence_reasons,
                coverage=coverage,
                reasons=reasons,
                primary_reason=primary,
                frame=frame,
                baselines=baselines[crew_id],
                deviations=deviations[crew_id],
                hypotheses=hypotheses[crew_id],
                crew_findings=crew_findings,
                environmental_alerts=environmental_hits,
                data_quality=data_quality,
                tests=tests,
                gamification=gamification,
                computed_at=iso(now),
                backfilled_recent=backfilled,
                pattern_description=descriptions[crew_id],
            )

        bundle = AnalysisBundle(
            snapshots=snapshots,
            crew_findings=crew_findings,
            environmental_alerts=environmental_hits,
            env_frame=env_frame,
            crew=crew_rows,
            events=events,
            computed_at=iso(now),
            locale=locale,
        )
        self._persist(bundle, baselines)
        return bundle

    def _confidence(
        self,
        hits: list[RuleHit],
        coverage: float,
        data_quality: list[dict[str, Any]],
        baselines: dict[str, Baseline],
    ) -> tuple[str, list[str]]:
        thresholds = load_thresholds().get("coverage", {})
        min_cov = float(thresholds.get("min_confidence_coverage", 0.4))
        good_cov = float(thresholds.get("good_coverage", 0.75))
        reasons: list[str] = []
        if coverage < min_cov:
            confidence = "low"
            reasons.append("low_coverage")
        elif coverage < good_cov:
            confidence = "medium"
            reasons.append("partial_coverage")
        else:
            confidence = "high"
        if data_quality:
            reasons.append("sensor_quality_flags")
            if confidence == "high":
                confidence = "medium"
        if any(b.origin == "population" for b in baselines.values()):
            reasons.append("population_baseline")
            if confidence == "high":
                confidence = "medium"
        if any(hit.level in {"orange", "red"} for hit in hits) and confidence == "low":
            reasons.append("urgent_with_limited_data")
        return confidence, reasons

    def _quality_snapshot(self, events: list[dict[str, Any]], astronaut_id: str) -> list[dict[str, Any]]:
        cutoff = utcnow() - timedelta(days=3)
        flags: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for event in reversed(events):
            if event.get("astronaut_id") != astronaut_id:
                continue
            try:
                if parse_iso(event["measured_at"]) < cutoff:
                    continue
            except Exception:
                continue
            if event.get("quality") == "ok":
                continue
            for reason in event.get("quality_reasons") or []:
                key = (event["measured_at"][:10], event["type"], reason)
                if key in seen:
                    continue
                seen.add(key)
                flags.append(
                    {
                        "date": event["measured_at"][:10],
                        "type": event["type"],
                        "quality": event.get("quality"),
                        "reason": reason,
                    }
                )
        return flags[:12]

    def _primary_reason(self, level: str, reasons: list[dict[str, Any]], locale: str) -> str:
        if level == "green":
            return (
                "No alert-level pattern in your recent data."
                if locale == "en"
                else "Nessun pattern di allarme nei tuoi dati recenti."
            )
        if level == "gray":
            for reason in reasons:
                if reason.get("kind") == "data_gap":
                    return reason["explanation"]
        if reasons:
            return str(reasons[0].get("explanation", ""))
        return "Review your status with the CMO." if locale == "en" else "Rivedi lo stato con il CMO."

    def _ensure_tests(
        self,
        astronaut_id: str,
        today: date,
        deviations: list[Deviation],
        baselines: dict[str, Baseline],
        data_quality: list[dict[str, Any]],
        coverage: float,
    ) -> list[dict[str, Any]]:
        rows = self.db.query(
            "SELECT * FROM tests WHERE astronaut_id = ? AND date = ? ORDER BY created_at ASC",
            (astronaut_id, today.isoformat()),
        )
        existing = [dict(row) for row in rows]
        for item in existing:
            item["why_en"], _, item["why_it"] = item["why"].partition("||")
        if existing:
            return existing
        last_rows = self.db.query(
            "SELECT test, MAX(date) AS last_date FROM tests WHERE astronaut_id = ? AND status = 'completed' GROUP BY test",
            (astronaut_id,),
        )
        last_tests = {row["test"]: row["last_date"] for row in last_rows}
        quality_flags = sorted({flag["reason"].replace("implausible_", "").replace("flatline_", "") for flag in data_quality})
        candidates = suggest_tests(
            deviations,
            baselines,
            quality_flags,
            last_tests,
            coverage,
            today,
        )
        created: list[dict[str, Any]] = []
        now = iso(utcnow())
        for candidate in candidates:
            test_id = f"test:{astronaut_id}:{today.isoformat()}:{candidate['test']}"
            self.db.execute(
                "INSERT OR IGNORE INTO tests (id, astronaut_id, date, test, why, minutes, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'suggested', ?)",
                (
                    test_id,
                    astronaut_id,
                    today.isoformat(),
                    candidate["test"],
                    candidate["why_en"] + "||" + candidate["why_it"],
                    candidate["minutes"],
                    now,
                ),
            )
            row = self.db.query_one("SELECT * FROM tests WHERE id = ?", (test_id,))
            if row:
                item = dict(row)
                item["why_en"], _, item["why_it"] = item["why"].partition("||")
                created.append(item)
        return created or existing

    def _recent_tests(self, astronaut_id: str, today: date) -> list[dict[str, Any]]:
        start = (today - timedelta(days=30)).isoformat()
        rows = self.db.query(
            "SELECT * FROM tests WHERE astronaut_id = ? AND date >= ? ORDER BY date DESC",
            (astronaut_id, start),
        )
        out = []
        for row in rows:
            item = dict(row)
            item["why_en"], _, item["why_it"] = item["why"].partition("||")
            out.append(item)
        return out

    def _persist(self, bundle: AnalysisBundle, baselines: dict[str, dict[str, Baseline]]) -> None:
        now = iso(utcnow())
        with self.db.transaction() as conn:
            for crew_id, snapshot in bundle.snapshots.items():
                conn.execute("DELETE FROM daily_features WHERE astronaut_id = ?", (crew_id,))
                for row in frame_to_rows(snapshot.frame, crew_id):
                    conn.execute(
                        "INSERT OR REPLACE INTO daily_features "
                        "(astronaut_id, date, metric, value, coverage, quality, n_obs) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            row["astronaut_id"],
                            row["date"],
                            row["metric"],
                            row["value"],
                            row["coverage"],
                            row["quality"],
                            row["n_obs"],
                        ),
                    )
                for row in baseline_rows(crew_id, baselines[crew_id], now):
                    conn.execute(
                        "INSERT OR REPLACE INTO baselines "
                        "(astronaut_id, metric, center, spread, n_obs, origin, frozen, version, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        row,
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO status_snapshots "
                    "(astronaut_id, level, reasons, confidence, coverage, computed_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        crew_id,
                        snapshot.level,
                        dumps(snapshot.reasons),
                        snapshot.confidence,
                        snapshot.coverage,
                        snapshot.computed_at,
                    ),
                )
            conn.execute("DELETE FROM crew_findings")
            for finding in bundle.crew_findings:
                conn.execute(
                    "INSERT INTO crew_findings "
                    "(id, window_start, window_end, metrics, direction, members, member_count, env_correlations, "
                    " confidence, status, description, description_it, coverage, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        finding.id,
                        finding.window_start,
                        finding.window_end,
                        dumps(finding.metrics),
                        finding.direction,
                        dumps(finding.members),
                        finding.member_count,
                        dumps(finding.env_correlations),
                        finding.confidence,
                        finding.status,
                        finding.description_en,
                        finding.description_it,
                        finding.coverage,
                        now,
                    ),
                )

    def trends(self, astronaut_id: str, days: int = 30, locale: str = "en") -> dict[str, Any]:
        bundle = self.bundle(locale)
        snapshot = bundle.snapshot(astronaut_id)
        thresholds = load_thresholds().get("population_ranges", {})
        frame = snapshot.frame[-days:] if days > 0 else snapshot.frame
        metrics: dict[str, Any] = {}
        for metric in FEATURE_METRICS:
            baseline = snapshot.baselines.get(metric)
            pop = thresholds.get(metric, {})
            points = []
            for day in frame:
                points.append(
                    {
                        "date": day.date.isoformat(),
                        "value": day.metrics.get(metric),
                        "quality": day.quality.get(metric),
                        "coverage": day.coverage,
                        "backfilled": day.backfilled,
                    }
                )
            metrics[metric] = {
                "label_en": _metric_label(metric, "en"),
                "label_it": _metric_label(metric, "it"),
                "unit": pop.get("unit", ""),
                "points": points,
                "baseline": {
                    "center": round(baseline.center, 2) if baseline else None,
                    "spread": round(baseline.spread, 2) if baseline else None,
                    "origin": baseline.origin if baseline else "population",
                    "frozen": baseline.frozen if baseline else False,
                },
            }
        return {
            "astronaut_id": astronaut_id,
            "days": days,
            "metrics": metrics,
            "computed_at": bundle.computed_at,
        }

    def environment_trends(self, days: int = 30) -> dict[str, Any]:
        bundle = self.bundle()
        thresholds = load_thresholds().get("population_ranges", {})
        frame = bundle.env_frame[-days:] if days > 0 else bundle.env_frame
        metrics: dict[str, Any] = {}
        for metric in ("co2_ppm", "cabin_temp_c", "humidity_pct", "noise_db", "radiation_usv", "pressure_kpa"):
            points = [
                {"date": row["date"], "value": row["metrics"].get(metric), "coverage": row["coverage"]}
                for row in frame
            ]
            metrics[metric] = {
                "label_en": _env_label(metric, "en"),
                "label_it": _env_label(metric, "it"),
                "unit": thresholds.get(metric, {}).get("unit", ""),
                "points": points,
            }
        return {"days": days, "metrics": metrics, "computed_at": bundle.computed_at}


def _metric_label(metric: str, locale: str) -> str:
    labels = {
        "resting_hr": ("Resting heart rate", "Frequenza a riposo"),
        "hrv_rmssd": ("Heart-rate variability", "Variabilità cardiaca"),
        "spo2": ("Oxygen saturation", "Saturazione di ossigeno"),
        "skin_temp": ("Skin temperature", "Temperatura cutanea"),
        "respiratory_rate": ("Respiratory rate", "Frequenza respiratoria"),
        "sleep_hours": ("Sleep duration", "Durata del sonno"),
        "sleep_efficiency": ("Sleep efficiency", "Efficienza del sonno"),
        "mood": ("Mood", "Umore"),
        "energy": ("Energy", "Energia"),
        "symptom_load": ("Symptom load", "Carico di sintomi"),
        "hydration": ("Hydration", "Idratazione"),
        "pain": ("Pain", "Dolore"),
        "activity_min": ("Activity", "Attività"),
    }
    return labels.get(metric, (metric, metric))[0 if locale == "en" else 1]


def _env_label(metric: str, locale: str) -> str:
    labels = {
        "co2_ppm": ("Cabin CO₂", "CO₂ in cabina"),
        "cabin_temp_c": ("Cabin temperature", "Temperatura in cabina"),
        "humidity_pct": ("Humidity", "Umidità"),
        "noise_db": ("Noise", "Rumore"),
        "radiation_usv": ("Radiation dose", "Dose di radiazioni"),
        "pressure_kpa": ("Cabin pressure", "Pressione in cabina"),
    }
    return labels.get(metric, (metric, metric))[0 if locale == "en" else 1]
