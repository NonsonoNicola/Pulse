---
id: protocol_chest_pain
title: Chest pain — emergency protocol
title_it: Dolore al petto — protocollo di emergenza
status: NEEDS_CLINICAL_REVIEW
severity: red
resources: [ecg, oxygen_supply, defibrillator, bp_cuff, stethoscope, aspirin, medication_cabinet]
reassess_minutes: 5
escalate_when_en:
  - Pain persists or worsens after rest
  - Breathing difficulty, fainting, or low oxygen
  - Abnormal ECG or unstable vital signs
escalate_when_it:
  - Il dolore persiste o peggiora a riposo
  - Difficoltà respiratoria, svenimento o ossigeno basso
  - ECG anomalo o parametri instabili
steps:
  - id: cp_stop
    en: Stop all activity. Sit upright or recline in the most comfortable position.
    it: Interrompi ogni attività. Siediti o sdraiati nella posizione più comoda.
    minutes: 1
  - id: cp_call_cmo
    en: Call the CMO now and tell them where the pain is, when it started, and what it feels like.
    it: Chiama subito il CMO e digli dove è il dolore, quando è iniziato e come si sente.
    minutes: 1
  - id: cp_vitals
    en: Measure oxygen saturation, heart rate, blood pressure and respiratory rate. Record the time.
    it: Misura saturazione, frequenza cardiaca, pressione e frequenza respiratoria. Registra l'ora.
    minutes: 3
  - id: cp_ecg
    en: Connect the ECG if available and transmit the tracing to the CMO.
    it: Collega l'ECG se disponibile e invia il tracciato al CMO.
    minutes: 4
  - id: cp_oxygen
    en: Prepare oxygen and the defibrillator. Use oxygen only as directed by the CMO or protocol.
    it: Prepara ossigeno e defibrillatore. Usa l'ossigeno solo come indicato dal CMO o dal protocollo.
    minutes: 2
  - id: cp_aspirin
    en: Ask the CMO before any medication. Confirm allergies and bleeding risk.
    it: Chiedi al CMO prima di qualsiasi farmaco. Verifica allergie e rischio di sanguinamento.
    minutes: 1
  - id: cp_sbar
    en: Generate the SBAR packet and send it with priority P0.
    it: Genera il pacchetto SBAR e invialo con priorità P0.
    minutes: 1
  - id: cp_reassess
    en: Reassess vital signs every 5 minutes and record any change.
    it: Rivaluta i parametri ogni 5 minuti e registra ogni cambiamento.
    minutes: 1
---
## Purpose
Stabilise and assess a crew member with possible cardiac chest pain while definitive care is delayed.

## Scope
CMO-led. The assistant may read these steps aloud and record actions but cannot add invasive instructions or medication doses.

## Key principle
The emergency mode starts from the deterministic phrase/symptom classifier, not from the LLM. Ground consultation happens in parallel.
