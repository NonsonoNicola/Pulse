---
id: protocol_fever
title: Fever and suspected infection
title_it: Febbre e sospetta infezione
status: NEEDS_CLINICAL_REVIEW
severity: orange
resources: [thermometer, bp_cuff, pulse_oximeter, stethoscope, oral_rehydration_salts, medication_cabinet, iv_fluids]
reassess_minutes: 60
escalate_when_en:
  - Breathing difficulty or low oxygen
  - Confusion, fainting, or severe dehydration
  - Rapid worsening or a second crew member with fever
escalate_when_it:
  - Difficoltà respiratoria o ossigeno basso
  - Confusione, svenimento o disidratazione grave
  - Peggioramento rapido o un secondo astronauta con febbre
steps:
  - id: fever_measure
    en: Measure oral temperature and repeat it in 15 minutes with the same device.
    it: Misura la temperatura orale e ripetila dopo 15 minuti con lo stesso dispositivo.
    minutes: 2
  - id: fever_vitals
    en: Record heart rate, blood pressure, oxygen saturation and respiratory rate.
    it: Registra frequenza cardiaca, pressione, saturazione e frequenza respiratoria.
    minutes: 3
  - id: fever_hydrate
    en: Drink fluids in small amounts. Use oral rehydration salts if intake is poor.
    it: Bevi a piccoli sorsi. Usa i sali reidratanti se bevi poco.
    minutes: 1
  - id: fever_cmo
    en: Contact the CMO with the temperature trend and symptom timeline.
    it: Contatta il CMO con il trend della temperatura e la cronologia dei sintomi.
    minutes: 1
  - id: fever_isolate
    en: If a contagious illness is suspected, limit close contact and use the agreed isolation steps.
    it: Se sospetti una malattia contagiosa, limita i contatti stretti e segui le misure di isolamento concordate.
    minutes: 1
  - id: fever_reassess
    en: Recheck temperature and symptoms in 60 minutes or sooner if worse.
    it: Ricontrolla temperatura e sintomi dopo 60 minuti o prima se peggiora.
    minutes: 1
---
## Purpose
Identify a possible infection early, prevent dehydration, and escalate before the crew member deteriorates.

## Scope
CMO-led. Antibiotics and doses require CMO confirmation and the calculator.
