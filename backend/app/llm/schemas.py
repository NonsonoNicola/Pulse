from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Level = Literal["green", "yellow", "orange", "red", "gray"]
Confidence = Literal["low", "medium", "high"]


class Observation(BaseModel):
    metric: str
    finding: str
    evidence_event_ids: list[str] = Field(default_factory=list)


class HypothesisOut(BaseModel):
    name: str
    support: list[str] = Field(default_factory=list)
    against: list[str] = Field(default_factory=list)
    card_ids: list[str] = Field(default_factory=list)


class SuggestedTest(BaseModel):
    test: str
    why: str
    minutes: int = 2


class CmoAction(BaseModel):
    action: str
    reason: str


class Assessment(BaseModel):
    triage_level: Level
    rule_level: Level
    summary_simple: str
    observations: list[Observation] = Field(default_factory=list)
    hypotheses: list[HypothesisOut] = Field(default_factory=list)
    confidence: Confidence = "medium"
    confidence_reasons: list[str] = Field(default_factory=list)
    do_now: list[str] = Field(default_factory=list)
    outside_protocol: bool = False
    reassess_in_minutes: int | None = None
    escalate_when: list[str] = Field(default_factory=list)
    suggested_tests: list[SuggestedTest] = Field(default_factory=list)
    questions_for_user: list[str] = Field(default_factory=list)
    questions_for_ground: list[str] = Field(default_factory=list)
    needs_cmo_confirmation: list[CmoAction] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    disclaimer_key: str = "disclaimer.clinical"
    warnings: list[str] = Field(default_factory=list)

    @field_validator("triage_level", "rule_level")
    @classmethod
    def _levels(cls, value: str) -> str:
        allowed = {"green", "yellow", "orange", "red", "gray"}
        if value not in allowed:
            raise ValueError(f"invalid level: {value}")
        return value

    def brief(self) -> dict:
        return {
            "triage_level": self.triage_level,
            "rule_level": self.rule_level,
            "summary_simple": self.summary_simple,
            "confidence": self.confidence,
            "outside_protocol": self.outside_protocol,
            "sources": self.sources,
        }


LEVEL_LABELS = {
    "en": {
        "green": "Green · no alert-level pattern",
        "yellow": "Yellow · attention",
        "orange": "Orange · clinical review soon",
        "red": "Red · emergency",
        "gray": "Gray · not enough data",
    },
    "it": {
        "green": "Verde · nessun pattern di allarme",
        "yellow": "Giallo · attenzione",
        "orange": "Arancio · valutazione clinica a breve",
        "red": "Rosso · emergenza",
        "gray": "Grigio · dati insufficienti",
    },
}

CONFIDENCE_LABELS = {
    "en": {"low": "Low confidence", "medium": "Moderate confidence", "high": "High confidence"},
    "it": {"low": "Confidenza bassa", "medium": "Confidenza moderata", "high": "Confidenza alta"},
}

DISCLAIMERS = {
    "en": {
        "clinical": (
            "Research prototype — not a medical device. These are suggestions, not a diagnosis. "
            "A CMO or flight surgeon decides on treatment."
        ),
        "draft": "Clinical content is a draft and needs review by a flight-medicine physician.",
    },
    "it": {
        "clinical": (
            "Prototipo di ricerca — non è un dispositivo medico. Questi sono suggerimenti, non una diagnosi. "
            "Le decisioni terapeutiche spettano al CMO o al flight surgeon."
        ),
        "draft": "Il contenuto clinico è una bozza e richiede la revisione di un medico di medicina spaziale.",
    },
}


def render_markdown(assessment: Assessment, locale: str = "en", explanation_level: str = "simple") -> str:
    lang = "it" if locale == "it" else "en"
    labels = LEVEL_LABELS[lang]
    lines: list[str] = [f"### {labels.get(assessment.triage_level, assessment.triage_level)}", ""]
    lines.append(assessment.summary_simple.strip())
    lines.append("")

    if explanation_level in {"detailed", "clinical"} and assessment.observations:
        lines.append("**" + ("What I observed" if lang == "en" else "Cosa ho osservato") + "**")
        for obs in assessment.observations[:6]:
            lines.append(f"- {obs.finding}")
        lines.append("")
        lines.append(
            f"**{CONFIDENCE_LABELS[lang][assessment.confidence]}**"
            + (f" — {', '.join(r.replace('_', ' ') for r in assessment.confidence_reasons)}" if assessment.confidence_reasons else "")
        )
        lines.append("")

    if assessment.do_now:
        lines.append("**" + ("What to do now" if lang == "en" else "Cosa fare ora") + "**")
        for index, step in enumerate(assessment.do_now, 1):
            lines.append(f"{index}. {step}")
        lines.append("")
    else:
        lines.append(
            "**" + ("What to do now" if lang == "en" else "Cosa fare ora") + "**: "
            + ("No extra action today. Keep your normal routine." if lang == "en" else "Nessuna azione extra oggi. Mantieni la routine normale.")
        )
        lines.append("")

    if assessment.reassess_in_minutes:
        lines.append(
            "**" + ("Reassess in" if lang == "en" else "Rivaluta tra") + f"** {assessment.reassess_in_minutes} "
            + ("minutes" if lang == "en" else "minuti")
        )
        lines.append("")

    if assessment.escalate_when:
        lines.append("**" + ("Escalate if" if lang == "en" else "Escalation se") + "**")
        for item in assessment.escalate_when[:4]:
            lines.append(f"- {item}")
        lines.append("")

    if assessment.suggested_tests:
        lines.append("**" + ("Suggested tests" if lang == "en" else "Test suggeriti") + "**")
        for test in assessment.suggested_tests[:3]:
            lines.append(f"- **{test.test.replace('_', ' ')}** ({test.minutes} min) — {test.why}")
        lines.append("")

    if assessment.hypotheses and explanation_level in {"detailed", "clinical"}:
        lines.append("**" + ("Working hypotheses" if lang == "en" else "Ipotesi di lavoro") + "**")
        for hypothesis in assessment.hypotheses[:3]:
            lines.append(f"- **{hypothesis.name}** — " + "; ".join(hypothesis.support[:3]))
        lines.append("")

    if assessment.questions_for_user and explanation_level != "simple":
        lines.append("**" + ("I need to ask" if lang == "en" else "Devo chiedere") + "**")
        for question in assessment.questions_for_user[:3]:
            lines.append(f"- {question}")
        lines.append("")

    if assessment.questions_for_ground:
        lines.append("**" + ("For the ground team" if lang == "en" else "Per il team a terra") + "**")
        for question in assessment.questions_for_ground[:4]:
            lines.append(f"- {question}")
        lines.append("")

    if assessment.needs_cmo_confirmation:
        lines.append("**" + ("Needs CMO confirmation" if lang == "en" else "Serve conferma del CMO") + "**")
        for action in assessment.needs_cmo_confirmation[:3]:
            lines.append(f"- {action.action} — {action.reason}")
        lines.append("")

    if assessment.sources:
        lines.append("**" + ("Sources" if lang == "en" else "Fonti") + "**: " + ", ".join(f"`{s}`" for s in assessment.sources))
        lines.append("")

    lines.append("> " + DISCLAIMERS[lang]["clinical"])
    if assessment.sources:
        lines.append("> " + DISCLAIMERS[lang]["draft"])
    return "\n".join(lines)
