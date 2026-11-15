from __future__ import annotations

import re
from typing import Any

from app.llm.schemas import Assessment, CmoAction, LEVEL_LABELS

LEVEL_ORDER = {"gray": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4}
CONF_ORDER = {"low": 0, "medium": 1, "high": 2}

DOSE_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|g|ml|cc|iu|units?|tablets?|pills?|capsules?|drops?|puffs?|sachets?)\b",
    re.IGNORECASE,
)
DIAGNOSTIC_PATTERNS = [
    (re.compile(r"\byou have\b", re.IGNORECASE), "the pattern is consistent with"),
    (re.compile(r"\bdiagnosis is\b", re.IGNORECASE), "working assessment is"),
    (re.compile(r"\bthis is definitely\b", re.IGNORECASE), "this may be"),
    (re.compile(r"\bdefinitely\b", re.IGNORECASE), "possibly"),
    (re.compile(r"\bno need to worry\b", re.IGNORECASE), "this needs monitoring"),
    (re.compile(r"\bnothing serious\b", re.IGNORECASE), "this needs monitoring"),
    (re.compile(r"\byou are fine\b", re.IGNORECASE), "this needs monitoring"),
]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def max_level(*levels: str) -> str:
    return max(levels, key=lambda level: LEVEL_ORDER.get(level, 0))


def max_confidence(*confidences: str) -> str:
    return min(confidences, key=lambda c: CONF_ORDER.get(c, 0))


def _clean_text(text: str, warnings: list[str], *, allow_doses: bool = False) -> tuple[str, bool, bool]:
    dose_found = False
    diagnostic_found = False
    cleaned = text
    if not allow_doses and DOSE_PATTERN.search(cleaned):
        sentences = SENTENCE_SPLIT.split(cleaned)
        kept = [s for s in sentences if not DOSE_PATTERN.search(s)]
        cleaned = " ".join(kept).strip() or "Ask the CMO for the exact dose and preparation."
        dose_found = True
        warnings.append("dose_numbers_removed")
    for pattern, replacement in DIAGNOSTIC_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub(replacement, cleaned)
            diagnostic_found = True
    if diagnostic_found:
        warnings.append("diagnostic_language_softened")
    return cleaned.strip(), dose_found, diagnostic_found


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9àèéìòù ]+", " ", text.lower()).strip()


def _is_protocol_step(text: str, allowed_steps: list[str]) -> bool:
    candidate = _normalize(text)
    if not candidate:
        return False
    for step in allowed_steps:
        normalized = _normalize(step)
        if not normalized:
            continue
        if candidate == normalized or candidate in normalized or normalized in candidate:
            return True
        candidate_terms = {t for t in candidate.split() if len(t) > 4}
        step_terms = {t for t in normalized.split() if len(t) > 4}
        if candidate_terms and len(candidate_terms & step_terms) / len(candidate_terms) >= 0.7:
            return True
    return False


def enforce(assessment: Assessment, context: dict[str, Any]) -> Assessment:
    """Code-level guardrails. Mutates and returns the assessment plus internal warnings."""
    warnings: list[str] = list(assessment.warnings)

    # 1. Read-only rule level and triage floor.
    rule_level = context.get("rule_level", assessment.rule_level)
    assessment.rule_level = rule_level
    if rule_level in {"yellow", "orange", "red"} and LEVEL_ORDER[assessment.triage_level] < LEVEL_ORDER[rule_level]:
        assessment.triage_level = rule_level
        warnings.append("triage_raised_to_rule_level")
    if assessment.triage_level == "green" and rule_level == "gray":
        # Gray is a data-quality state, not a clinical downgrade; keep the triage but make the
        # uncertainty explicit in the UI via rule_level.
        warnings.append("rule_level_gray")

    # 2. Steps must exist verbatim (or near-verbatim) in a supplied protocol.
    allowed_steps: list[str] = context.get("allowed_steps", [])
    if assessment.do_now:
        kept: list[str] = []
        removed = False
        for step in assessment.do_now:
            if not allowed_steps or _is_protocol_step(step, allowed_steps):
                kept.append(step)
            else:
                removed = True
        if removed:
            assessment.outside_protocol = True
            assessment.confidence = max_confidence(assessment.confidence, "medium")
            warnings.append("step_outside_protocol_removed")
            assessment.questions_for_ground.append(
                "The assistant proposed an action outside the validated protocol. Please review the plan."
            )
            allowed = "; ".join(allowed_steps[:2])
            if kept:
                assessment.do_now = kept
            elif allowed:
                assessment.do_now = [allowed_steps[0]]
        if assessment.outside_protocol:
            assessment.confidence = max_confidence(assessment.confidence, "medium")
            assessment.questions_for_ground.append(
                "The situation may be outside the protocol; what is the preferred next step on the ground?"
            )

    # 3. No dose numbers in free text.
    texts = [
        ("summary_simple", assessment.summary_simple),
        *[(f"observation_{i}", obs.finding) for i, obs in enumerate(assessment.observations)],
        *[(f"hypothesis_{i}", support) for i, h in enumerate(assessment.hypotheses) for support in h.support],
        *[(f"do_now_{i}", step) for i, step in enumerate(assessment.do_now)],
        *[(f"escalate_{i}", item) for i, item in enumerate(assessment.escalate_when)],
        *[(f"test_{i}", test.why) for i, test in enumerate(assessment.suggested_tests)],
        *[(f"ground_{i}", q) for i, q in enumerate(assessment.questions_for_ground)],
        *[(f"cmo_{i}", action.reason) for i, action in enumerate(assessment.needs_cmo_confirmation)],
    ]
    dose_removed = False
    diagnostic_softened = False
    clean: dict[str, str] = {}
    for key, text in texts:
        cleaned, dose, diagnostic = _clean_text(text, warnings)
        clean[key] = cleaned
        dose_removed = dose_removed or dose
        diagnostic_softened = diagnostic_softened or diagnostic
    assessment.summary_simple = clean.get("summary_simple", assessment.summary_simple)
    for i, obs in enumerate(assessment.observations):
        obs.finding = clean.get(f"observation_{i}", obs.finding)
    for i, hypothesis in enumerate(assessment.hypotheses):
        hypothesis.support = [
            clean.get(f"hypothesis_{i}", support) for support in hypothesis.support
        ]
    assessment.do_now = [clean.get(f"do_now_{i}", step) for i, step in enumerate(assessment.do_now)]
    assessment.escalate_when = [
        clean.get(f"escalate_{i}", item) for i, item in enumerate(assessment.escalate_when)
    ]
    for i, test in enumerate(assessment.suggested_tests):
        test.why = clean.get(f"test_{i}", test.why)
    assessment.questions_for_ground = [
        clean.get(f"ground_{i}", q) for i, q in enumerate(assessment.questions_for_ground)
    ]
    for i, action in enumerate(assessment.needs_cmo_confirmation):
        action.reason = clean.get(f"cmo_{i}", action.reason)
    if dose_removed:
        assessment.confidence = max_confidence(assessment.confidence, "medium")
        assessment.needs_cmo_confirmation.append(
            CmoAction(
                action="Confirm any medication and dose",
                reason="Dose numbers are only allowed from the deterministic calculator, with CMO confirmation.",
            )
        )
    if diagnostic_softened:
        assessment.confidence = max_confidence(assessment.confidence, "medium")

    # 4. Citations must exist. Clinical recommendations need at least one valid card.
    valid_cards = set(context.get("valid_card_ids", []))
    assessment.sources = [card for card in assessment.sources if card in valid_cards]
    for hypothesis in assessment.hypotheses:
        hypothesis.card_ids = [card for card in hypothesis.card_ids if card in valid_cards]
    if not assessment.sources and context.get("default_card_id") in valid_cards:
        assessment.sources = [context["default_card_id"]]
        warnings.append("citation_added_from_context")
    if assessment.sources and not any(card in valid_cards for card in assessment.sources):
        assessment.sources = []
    clinical_action = bool(assessment.do_now) or any(h.card_ids for h in assessment.hypotheses)
    if clinical_action and not assessment.sources:
        assessment.confidence = max_confidence(assessment.confidence, "low")
        assessment.outside_protocol = True
        assessment.questions_for_ground.append(
            "No validated knowledge card supports this plan. Please advise on the next step."
        )
        warnings.append("no_source_citation")
    if not assessment.questions_for_ground and assessment.confidence == "low":
        assessment.questions_for_ground.append("Low confidence: please confirm the interpretation and plan.")

    # 5. Evidence ids must be real; drop observations without provenance.
    valid_evidence = set(context.get("evidence_ids", []))
    if valid_evidence:
        kept_observations = []
        for observation in assessment.observations:
            observation.evidence_event_ids = [e for e in observation.evidence_event_ids if e in valid_evidence][:5]
            if observation.evidence_event_ids:
                kept_observations.append(observation)
        if len(kept_observations) != len(assessment.observations):
            warnings.append("observations_without_evidence_removed")
        assessment.observations = kept_observations

    # 6. Resource feasibility.
    inventory_ids = set(context.get("inventory_ids", []))
    protocol_resources = [r for r in context.get("protocol_resources", []) if r]
    missing = [r for r in protocol_resources if r not in inventory_ids]
    if missing:
        warnings.append("resource_missing:" + ",".join(missing))
        assessment.needs_cmo_confirmation.append(
            CmoAction(
                action="Choose an alternative for: " + ", ".join(missing),
                reason="The protocol resource is not listed in the onboard inventory.",
            )
        )
        assessment.confidence = max_confidence(assessment.confidence, "medium")

    # 7. No promises / always disclaimer.
    assessment.disclaimer_key = "disclaimer.clinical"
    assessment.warnings = sorted(set(warnings))
    return assessment


def level_label(level: str, locale: str = "en") -> str:
    return LEVEL_LABELS.get(locale, LEVEL_LABELS["en"]).get(level, level)
