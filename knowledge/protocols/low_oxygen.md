---
id: protocol_low_oxygen
title: Low oxygen or breathing difficulty
title_it: Ossigeno basso o difficoltà respiratoria
status: NEEDS_CLINICAL_REVIEW
severity: red
resources: [pulse_oximeter, oxygen_supply, stethoscope, ecg, bp_cuff]
reassess_minutes: 5
escalate_when_en:
  - Oxygen stays low after a second measurement
  - Laboured breathing, confusion, or fainting
  - Chest pain or blue lips
escalate_when_it:
  - L'ossigeno resta basso dopo una seconda misura
  - Respiro faticoso, confusione o svenimento
  - Dolore al petto o labbra blu
steps:
  - id: ox_sit
    en: Sit upright, stop activity, and loosen tight clothing.
    it: Siediti, interrompi l'attività e allenta gli indumenti stretti.
    minutes: 1
  - id: ox_repeat
    en: Repeat oxygen saturation with a second device and check the probe placement.
    it: Ripeti la saturazione con un secondo dispositivo e controlla la posizione del sensore.
    minutes: 2
  - id: ox_call_cmo
    en: Call the CMO and report both readings, breathing rate and how the person looks.
    it: Chiama il CMO e riporta entrambe le letture, la frequenza respiratoria e l'aspetto della persona.
    minutes: 1
  - id: ox_environment
    en: Check cabin oxygen, CO2 and the scrubber. Move away from smoke or contaminants.
    it: Controlla ossigeno, CO2 e scrubber in cabina. Allontanati da fumo o contaminanti.
    minutes: 2
  - id: ox_oxygen
    en: Prepare oxygen. Use it only as directed by the CMO or protocol.
    it: Prepara l'ossigeno. Usalo solo come indicato dal CMO o dal protocollo.
    minutes: 2
  - id: ox_sbar
    en: Generate an SBAR packet with both sensor readings and the environmental data.
    it: Genera un pacchetto SBAR con entrambe le letture e i dati ambientali.
    minutes: 1
  - id: ox_reassess
    en: Reassess breathing and oxygen every 5 minutes until stable.
    it: Rivaluta respiro e ossigeno ogni 5 minuti finché non è stabile.
    minutes: 1
---
## Purpose
Distinguish true hypoxaemia from sensor error, correct the environment, and stabilise the crew member.

## Scope
Any crew member can start the first steps. The CMO leads the clinical decisions.
