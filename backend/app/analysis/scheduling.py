from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.analysis.baseline import Baseline
from app.analysis.drift import Deviation


@dataclass
class TestCandidate:
    test: str
    why_en: str
    why_it: str
    minutes: int
    value: float
    urgency: float

    @property
    def score(self) -> float:
        return (self.value + self.urgency) / max(1, self.minutes)


def suggest_tests(
    deviations: list[Deviation],
    baselines: dict[str, Baseline],
    quality_flags: list[str],
    last_tests: dict[str, str],
    coverage: float,
    today: date,
    budget_minutes: int = 5,
) -> list[dict[str, Any]]:
    """Active sensing heuristic: expected information gain + urgency, divided by time cost."""
    by_metric = {d.metric: d for d in deviations}
    candidates: list[TestCandidate] = []

    temp = by_metric.get("skin_temp")
    if temp and (temp.z > 1.0 or temp.quality == "suspect"):
        candidates.append(
            TestCandidate(
                test="oral_temperature",
                why_en="Your skin temperature is above your usual range. One oral reading helps confirm whether this is real.",
                why_it="La temperatura cutanea è sopra il tuo intervallo abituale. Una misura orale aiuta a capire se è reale.",
                minutes=2,
                value=min(1.0, abs(temp.z) / 3),
                urgency=0.8 if temp.z > 1.5 else 0.5,
            )
        )

    spo2 = by_metric.get("spo2")
    if any("spo2" in flag for flag in quality_flags) or (spo2 and (spo2.z < -1.5 or spo2.quality == "suspect")):
        candidates.append(
            TestCandidate(
                test="manual_spo2_recheck",
                why_en="The oxygen readings disagree with your other signals. A second device gives a cleaner picture.",
                why_it="Le letture di ossigeno non concordano con gli altri segnali. Un secondo dispositivo dà un quadro più chiaro.",
                minutes=1,
                value=0.9,
                urgency=0.8,
            )
        )

    hr = by_metric.get("resting_hr")
    if hr and abs(hr.z) >= 1.2:
        candidates.append(
            TestCandidate(
                test="blood_pressure",
                why_en="Your resting heart rate has shifted for several days. Blood pressure adds context in two minutes.",
                why_it="La frequenza a riposo è cambiata da alcuni giorni. La pressione aggiunge contesto in due minuti.",
                minutes=2,
                value=min(0.8, abs(hr.z) / 4),
                urgency=0.4,
            )
        )

    hydration = by_metric.get("hydration")
    if hydration and hydration.z < -1.0:
        candidates.append(
            TestCandidate(
                test="weight_and_urine_check",
                why_en="Hydration reports are low. Weight and urine colour are quick, practical checks.",
                why_it="L'idratazione riportata è bassa. Peso e colore delle urine sono controlli rapidi e pratici.",
                minutes=2,
                value=0.6,
                urgency=0.3,
            )
        )

    if coverage < 0.5:
        candidates.append(
            TestCandidate(
                test="baseline_refresh",
                why_en="Recent coverage is low. A few structured measurements rebuild your baseline faster than waiting.",
                why_it="La copertura recente è bassa. Alcune misure strutturate ricostruiscono la baseline più in fretta.",
                minutes=3,
                value=0.7,
                urgency=0.2,
            )
        )

    if not candidates:
        # Fixed-cadence fallback: weigh once per week and a BP check every two weeks.
        if _days_since(last_tests.get("weight"), today) >= 7:
            candidates.append(
                TestCandidate(
                    test="weight",
                    why_en="Weekly weight keeps fluid and muscle trends readable. It takes one minute.",
                    why_it="Il peso settimanale tiene leggibili i trend di liquidi e massa muscolare. Richiede un minuto.",
                    minutes=1,
                    value=0.35,
                    urgency=0.1,
                )
            )
        if _days_since(last_tests.get("blood_pressure"), today) >= 14:
            candidates.append(
                TestCandidate(
                    test="blood_pressure",
                    why_en="Your routine blood-pressure check is due. It helps interpret future heart-rate changes.",
                    why_it="È ora del controllo routine della pressione. Aiuta a interpretare futuri cambi della frequenza cardiaca.",
                    minutes=2,
                    value=0.25,
                    urgency=0.1,
                )
            )

    candidates.sort(key=lambda c: c.score, reverse=True)
    if coverage < 0.4:
        baseline_only = [c for c in candidates if c.test == "baseline_refresh"]
        candidates = baseline_only
    selected: list[dict[str, Any]] = []
    used = 0
    for candidate in candidates:
        if used + candidate.minutes > budget_minutes:
            continue
        last = last_tests.get(candidate.test)
        if _days_since(last, today) < 2:
            continue
        selected.append(
            {
                "test": candidate.test,
                "why_en": candidate.why_en,
                "why_it": candidate.why_it,
                "minutes": candidate.minutes,
                "score": round(candidate.score, 2),
            }
        )
        used += candidate.minutes
        if len(selected) >= 2:
            break
    return selected


def _days_since(last: str | None, today: date) -> int:
    if not last:
        return 999
    try:
        return (today - date.fromisoformat(last[:10])).days
    except ValueError:
        return 999
