from __future__ import annotations

import re
from typing import Any

from app.analysis.service import AstronautSnapshot
from app.core.config import load_inventory, load_symptoms
from app.core.timeutil import parse_iso
from app.llm.schemas import Assessment, CmoAction, HypothesisOut, Observation, SuggestedTest
from app.rag.store import KnowledgeBase


def _localized(locale: str, en: str, it: str) -> str:
    return it if locale == "it" else en


def _metric_label(metric: str, locale: str) -> str:
    labels = {
        "resting_hr": ("resting heart rate", "frequenza a riposo"),
        "hrv_rmssd": ("heart-rate variability", "variabilità cardiaca"),
        "spo2": ("oxygen saturation", "saturazione di ossigeno"),
        "skin_temp": ("skin temperature", "temperatura cutanea"),
        "respiratory_rate": ("respiratory rate", "frequenza respiratoria"),
        "sleep_hours": ("sleep duration", "durata del sonno"),
        "sleep_efficiency": ("sleep efficiency", "efficienza del sonno"),
        "mood": ("mood", "umore"),
        "energy": ("energy", "energia"),
        "symptom_load": ("symptom load", "carico di sintomi"),
        "hydration": ("hydration", "idratazione"),
        "pain": ("pain", "dolore"),
        "activity_min": ("activity", "attività"),
    }
    return labels.get(metric, (metric, metric))[1 if locale == "it" else 0]


def _evidence_for_metric(
    events: list[dict[str, Any]], astronaut_id: str, metric: str, days: int = 10
) -> list[str]:
    from app.core.timeutil import utcnow

    keys = {"pain": "pain_score"}.get(metric, metric)
    cutoff = utcnow().timestamp() - days * 86400
    out: list[str] = []
    for event in reversed(events):
        if event.get("astronaut_id") != astronaut_id:
            continue
        payload = event.get("payload") or {}
        present = keys in payload
        if metric == "pain":
            present = isinstance(payload.get("pain"), dict) or "pain_score" in payload
        if not present:
            continue
        try:
            if parse_iso(event["measured_at"]).timestamp() < cutoff:
                continue
        except Exception:
            continue
        out.append(event["id"])
        if len(out) >= 3:
            break
    return out


def _choose_protocol(snapshot: AstronautSnapshot, forced_protocol: str | None) -> str | None:
    if forced_protocol:
        return forced_protocol
    personal = sorted(
        [reason for reason in snapshot.reasons if reason.get("protocol")],
        key=lambda r: ({"gray": 0, "green": 1, "yellow": 2, "orange": 3, "red": 4}.get(r.get("level", ""), 0)),
        reverse=True,
    )
    red_hits = [reason for reason in personal if reason.get("level") == "red"]
    if red_hits:
        return red_hits[0]["protocol"]
    if any("spo2" in flag.get("reason", "") for flag in snapshot.data_quality):
        return "low_oxygen"
    if snapshot.crew_findings and any(
        hit.level in {"orange", "red"} and hit.protocol for hit in snapshot.environmental_alerts
    ):
        return next(hit.protocol for hit in snapshot.environmental_alerts if hit.level in {"orange", "red"} and hit.protocol)
    if personal:
        return personal[0]["protocol"]
    env = [hit for hit in snapshot.environmental_alerts if hit.level in {"orange", "red"} and hit.protocol]
    if env:
        return env[0].protocol
    return None


def _dedupe_sentences(parts: list[str], max_sentences: int = 5) -> str:
    """Join fragments, dropping exact duplicate sentences and enforcing a length budget."""
    seen: set[str] = set()
    sentences: list[str] = []
    for part in parts:
        for sentence in re.split(r"(?<=[.!?])\s+", (part or "").strip()):
            sentence = sentence.strip()
            if not sentence:
                continue
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            sentences.append(sentence)
            if len(sentences) >= max_sentences:
                return " ".join(sentences)
    return " ".join(sentences)


def _sensor_quality_text(locale: str) -> str:
    return _localized(
        locale,
        "One sensor reading conflicts with your other signals; repeat it with a second device. This is a data-quality issue, not an accusation.",
        "Una lettura del sensore non concorda con gli altri segnali; ripetila con un secondo dispositivo. È un problema di qualità del dato, non un'accusa.",
    )


def _summary(snapshot: AstronautSnapshot, locale: str, protocol_key: str | None, emergency: bool) -> str:
    level = snapshot.level
    if emergency or level == "red":
        first_reason = snapshot.primary_reason
        if protocol_key == "mental_crisis":
            return _localized(
                locale,
                "I'm glad you told me. You deserve support right now. Stay with the CMO and follow the steps below one at a time. You are not alone.",
                "Sono contento che tu me l'abbia detto. Meriti supporto adesso. Resta con il CMO e segui i passi qui sotto uno alla volta. Non sei solo.",
            )
        return _localized(
            locale,
            f"{first_reason} This needs immediate assessment. Stop activity and follow the steps below; the CMO has been alerted and a consultation packet is being prepared. Do not wait for the ground reply.",
            f"{first_reason} Serve una valutazione immediata. Interrompi l'attività e segui i passi qui sotto; il CMO è stato avvisato e stiamo preparando un pacchetto di consulto. Non aspettare la risposta da Terra.",
        )
    if level == "orange":
        parts = [
            reason["explanation"]
            for reason in snapshot.reasons[:2]
            if reason.get("rule_id") not in {"data_gap", "rule_sensor_quality"}
        ]
        if snapshot.data_quality:
            parts.append(_sensor_quality_text(locale))
        parts.append(
            _localized(
                locale,
                "This is above your personal baseline and needs a clinical review soon. A CMO confirmation and a focused measurement are the next steps. This is a suggestion, not a diagnosis.",
                "Questo è sopra la tua baseline personale e richiede una valutazione clinica a breve. La conferma del CMO e una misura mirata sono i prossimi passi. È un suggerimento, non una diagnosi.",
            )
        )
        return _dedupe_sentences(parts, max_sentences=5)
    if level == "yellow":
        parts = []
        sensor_issue = bool(snapshot.data_quality) or any(
            reason.get("rule_id") == "rule_sensor_quality" for reason in snapshot.reasons
        )
        personal = [
            reason["explanation"]
            for reason in snapshot.reasons
            if reason.get("rule_id") not in {"data_gap", "rule_sensor_quality"}
        ]
        if sensor_issue:
            parts.append(_sensor_quality_text(locale))
            if personal:
                parts.append(personal[0])
        else:
            if personal:
                parts.append(personal[0])
            if snapshot.crew_findings:
                finding = snapshot.crew_findings[0]
                parts.append(finding.description_it if locale == "it" else finding.description_en)
            elif len(personal) > 1:
                parts.append(personal[1])
        if snapshot.crew_findings and snapshot.environmental_alerts and not sensor_issue:
            env = snapshot.environmental_alerts[0]
            parts.append(
                _localized(
                    locale,
                    f"Cabin CO₂ is {env.value_text} over the last {env.days} days; treating the shared environment is the first lever.",
                    f"La CO₂ in cabina è {env.value_text} negli ultimi {env.days} giorni; agire sull'ambiente condiviso è la prima leva.",
                )
            )
        parts.append(
            _localized(
                locale,
                "Start with the actions below and reassess. This is a suggestion, not a diagnosis.",
                "Inizia dalle azioni qui sotto e rivaluta. È un suggerimento, non una diagnosi.",
            )
        )
        return _dedupe_sentences(parts, max_sentences=6) or snapshot.primary_reason
    if level == "gray":
        return _localized(
            locale,
            "There is not enough recent data to assess you. Recover the missing days or check in when you can; the system will not treat missing data as a health signal.",
            "Non ci sono dati recenti sufficienti per valutarti. Recupera i giorni mancanti o fai il check-in quando puoi; il sistema non tratta i dati mancanti come un segnale di salute.",
        )
    return _localized(
        locale,
        "Your recent data are within your usual range. No alert-level pattern today. Keep the same measurement routine; no extra action is needed.",
        "I tuoi dati recenti sono nel tuo intervallo abituale. Nessun pattern di allarme oggi. Mantieni la stessa routine di misura; non serve un'azione extra.",
    )


def _questions(
    snapshot: AstronautSnapshot, locale: str, protocol_key: str | None, emergency: bool
) -> list[str]:
    if emergency or snapshot.level == "red":
        if protocol_key == "mental_crisis":
            return [
                _localized(locale, "Are you safe right now?", "Sei al sicuro adesso?"),
                _localized(locale, "Is someone staying with you?", "C'è qualcuno con te?"),
            ]
        return [
            _localized(locale, "Is the symptom still present right now?", "Il sintomo è ancora presente adesso?"),
            _localized(locale, "Is it getting better, worse, or staying the same?", "Sta migliorando, peggiorando o resta uguale?"),
        ]
    if snapshot.level == "gray":
        return [
            _localized(locale, "Do you have the missing days' readings on your wearable?", "Hai le letture dei giorni mancanti sul wearable?"),
            _localized(locale, "Was there a blackout or a device problem?", "C'è stato un blackout o un problema al dispositivo?"),
        ]
    if any("spo2" in flag.get("reason", "") for flag in snapshot.data_quality):
        return [
            _localized(locale, "Do you feel short of breath, or is this only the sensor reading?", "Hai fiato corto o è solo la lettura del sensore?"),
            _localized(locale, "Do your fingers feel cold or did the sensor move?", "Hai le dita fredde o il sensore si è spostato?"),
        ]
    labels = [_metric_label(dev.metric, locale) for dev in snapshot.deviations[:2]]
    return [
        _localized(
            locale,
            f"Have you noticed anything else with your {', '.join(labels) or 'symptoms'} in the last few days?",
            f"Hai notato altro insieme a {', '.join(labels) or 'sintomi'} negli ultimi giorni?",
        ),
        _localized(locale, "Is it getting better, worse, or staying the same?", "Sta migliorando, peggiorando o resta uguale?"),
    ]


def compose(
    snapshot: AstronautSnapshot,
    kb: KnowledgeBase,
    events: list[dict[str, Any]],
    mission: dict[str, Any],
    locale: str = "en",
    explanation_level: str = "simple",
    user_message: str = "",
    forced_protocol: str | None = None,
    emergency: bool = False,
) -> Assessment:
    protocol_key = _choose_protocol(snapshot, forced_protocol)
    protocol = kb.protocol(protocol_key) if protocol_key else None
    step_texts = [step.get(locale) or step.get("en", "") for step in (protocol or {}).get("steps", [])]

    # Retrieval query combines the structured pattern, crew context and user wording.
    crew_text = snapshot.crew_findings[0].description_en if snapshot.crew_findings else ""
    query = " ".join(
        part
        for part in [
            snapshot.pattern_description,
            crew_text,
            user_message,
            " ".join(h.title for h in snapshot.hypotheses[:2]),
            " ".join(reason.get("explanation", "") for reason in snapshot.reasons[:2]),
        ]
        if part
    )
    rag_hits = kb.search(query, habitat=mission.get("id"), top_k=5) if query else []
    sources: list[str] = []
    for hypothesis in snapshot.hypotheses[:3]:
        if hypothesis.card_id and hypothesis.card_id not in sources:
            sources.append(hypothesis.card_id)
    for reason in snapshot.reasons:
        card_id = reason.get("card_id")
        if card_id and card_id not in sources:
            sources.append(card_id)
    for hit in snapshot.environmental_alerts:
        card_id = hit.card_id
        if card_id and card_id not in sources:
            sources.append(card_id)
    for hit in rag_hits:
        if hit["card_id"] not in sources:
            sources.append(hit["card_id"])
    sources = sources[:5]

    observations: list[Observation] = []
    for deviation in snapshot.deviations[:4]:
        evidence = _evidence_for_metric(events, snapshot.astronaut_id, deviation.metric)
        if not evidence:
            continue
        direction = _localized(locale, "above", "sopra") if deviation.z > 0 else _localized(locale, "below", "sotto")
        pct = f"{abs(deviation.percent):.0f}%" if deviation.percent is not None else f"{abs(deviation.z):.1f}σ"
        observations.append(
            Observation(
                metric=deviation.metric,
                finding=_localized(
                    locale,
                    f"{_metric_label(deviation.metric, locale).capitalize()} is {pct} {direction} your personal baseline ({deviation.z:+.1f}σ).",
                    f"{_metric_label(deviation.metric, locale).capitalize()} è {pct} {direction} la tua baseline personale ({deviation.z:+.1f}σ).",
                ),
                evidence_event_ids=evidence,
            )
        )
    if snapshot.data_quality:
        quality_event_ids = [
            event["id"]
            for event in events
            if event.get("astronaut_id") == snapshot.astronaut_id and event.get("quality") == "suspect"
        ][-3:]
        if quality_event_ids:
            observations.append(
                Observation(
                    metric="spo2",
                    finding=_localized(
                        locale,
                        "Oxygen readings conflict with heart rate and breathing; they are marked suspect and excluded from the baseline.",
                        "Le letture di ossigeno non concordano con frequenza cardiaca e respiro; sono marcate sospette ed escluse dalla baseline.",
                    ),
                    evidence_event_ids=quality_event_ids,
                )
            )

    hypotheses = [
        HypothesisOut(
            name=hypothesis.title,
            support=hypothesis.support,
            against=hypothesis.against,
            card_ids=[hypothesis.card_id],
        )
        for hypothesis in snapshot.hypotheses[:3]
    ]

    if emergency or snapshot.level == "red":
        do_now = step_texts[:4]
        reassess = int((protocol or {}).get("reassess_minutes", 5))
        confidence = "high" if snapshot.confidence == "high" else "medium"
        outside = False
    elif snapshot.level in {"orange", "yellow"} and step_texts:
        do_now = step_texts[:3]
        reassess = int((protocol or {}).get("reassess_minutes", 60 if snapshot.level == "orange" else 1440))
        confidence = snapshot.confidence
        outside = False
    else:
        do_now = []
        reassess = 1440 if snapshot.level == "green" else None
        confidence = snapshot.confidence
        outside = False
    if protocol_key is None and do_now:
        outside = True

    escalate = []
    if protocol:
        escalate = [
            item
            for item in (protocol.get(f"escalate_when_{locale}") or protocol.get("escalate_when_en", []))
        ]
    if not escalate:
        escalate = [
            _localized(locale, "Chest pain, severe breathlessness, fainting, or confusion.", "Dolore al petto, fiato corto grave, svenimento o confusione."),
            _localized(locale, "Symptoms keep worsening despite the steps above.", "I sintomi peggiorano nonostante i passi sopra."),
        ]

    tests = [
        SuggestedTest(
            test=test["test"],
            why=test.get(f"why_{locale}") or test.get("why_en", ""),
            minutes=int(test.get("minutes", 2)),
        )
        for test in snapshot.tests[:2]
    ]

    questions_ground: list[str] = []
    if snapshot.level in {"orange", "red"} or emergency:
        questions_ground = [
            _localized(
                locale,
                "Do these findings change the working plan? Please state the preferred next step and reassessment interval.",
                "Questi reperti cambiano il piano di lavoro? Indica il prossimo passo preferito e l'intervallo di rivalutazione.",
            ),
            _localized(
                locale,
                f"Any contraindication to the onboard resources for this case? Current link delay: {mission.get('link', {}).get('description', 'unknown')}.",
                f"Ci sono controindicazioni alle risorse di bordo per questo caso? Ritardo attuale del link: {mission.get('link', {}).get('description', 'sconosciuto')}.",
            ),
        ]
    elif snapshot.confidence == "low" or outside:
        questions_ground = [
            _localized(locale, "Low confidence on board. Please confirm interpretation and next steps.", "Confidenza bassa a bordo. Confermare interpretazione e prossimi passi.")
        ]
    if snapshot.level in {"yellow", "orange", "red"} and snapshot.crew_findings:
        questions_ground.append(
            _localized(
                locale,
                "Crew-wide pattern detected; should we prioritise an environmental intervention before individual workups?",
                "Rilevato un pattern di crew; dobbiamo prioritizzare un intervento ambientale prima degli accertamenti individuali?",
            )
        )

    cmo_actions: list[CmoAction] = []
    if emergency or snapshot.level == "red":
        cmo_actions.append(
            CmoAction(
                action=_localized(locale, "Any medication or procedure", "Qualsiasi farmaco o procedura"),
                reason=_localized(locale, "Irreversible actions require CMO confirmation.", "Le azioni irreversibili richiedono la conferma del CMO."),
            )
        )
    if protocol_key == "chest_pain":
        cmo_actions.append(
            CmoAction(
                action=_localized(locale, "Aspirin and oxygen decisions", "Decisioni su aspirina e ossigeno"),
                reason=_localized(locale, "Check allergy and bleeding risk before any medication.", "Verifica allergie e rischio di sanguinamento prima di ogni farmaco."),
            )
        )

    summary = _summary(snapshot, locale, protocol_key, emergency)

    return Assessment(
        triage_level=snapshot.level,
        rule_level=snapshot.level,
        summary_simple=summary,
        observations=observations,
        hypotheses=hypotheses,
        confidence=confidence,
        confidence_reasons=list(snapshot.confidence_reasons),
        do_now=do_now,
        outside_protocol=outside,
        reassess_in_minutes=reassess,
        escalate_when=escalate[:5],
        suggested_tests=tests,
        questions_for_user=_questions(snapshot, locale, protocol_key, emergency),
        questions_for_ground=questions_ground,
        needs_cmo_confirmation=cmo_actions,
        sources=sources,
        disclaimer_key="disclaimer.clinical",
    )


def composer_context(
    snapshot: AstronautSnapshot, kb: KnowledgeBase, mission: dict[str, Any]
) -> dict[str, Any]:
    protocol_key = _choose_protocol(snapshot, None)
    protocol = kb.protocol(protocol_key) or {}
    inventory = {item["id"] for item in load_inventory().get("items", [])}
    symptoms = load_symptoms().get("symptoms", [])
    return {
        "rule_level": snapshot.level,
        "protocol": protocol_key,
        "protocol_resources": protocol.get("resources", []),
        "inventory_ids": sorted(inventory),
        "valid_card_ids": [card["id"] for card in kb.cards()],
        "default_card_id": snapshot.hypotheses[0].card_id if snapshot.hypotheses else None,
        "evidence_ids": [event["id"] for event in []],
        "symptom_catalog": symptoms,
        "mission": mission,
        "snapshot": snapshot,
    }
