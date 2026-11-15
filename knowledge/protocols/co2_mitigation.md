---
id: protocol_co2_mitigation
title: Elevated cabin CO2
title_it: CO2 elevata in cabina
status: NEEDS_CLINICAL_REVIEW
severity: yellow
resources: []
reassess_minutes: 240
escalate_when_en:
  - Confusion, vomiting or severe drowsiness
  - CO2 remains high after corrective actions
  - Crew-wide deterioration
escalate_when_it:
  - Confusione, vomito o sonnolenza marcata
  - La CO2 resta alta dopo le correzioni
  - Peggioramento di tutta la crew
steps:
  - id: co2_verify
    en: Verify the CO2 reading with a second sensor and check the scrubber status.
    it: Verifica la CO2 con un secondo sensore e controlla lo stato dello scrubber.
    minutes: 2
  - id: co2_ventilate
    en: Increase ventilation and airflow. Reduce strenuous activity.
    it: Aumenta ventilazione e flusso d'aria. Riduci l'attività fisica intensa.
    minutes: 2
  - id: co2_move
    en: Move the crew to the best-ventilated module if CO2 remains high.
    it: Sposta la crew nel modulo meglio ventilato se la CO2 resta alta.
    minutes: 5
  - id: co2_report
    en: Tell the CMO and record the crew symptom pattern and environmental readings.
    it: Avvisa il CMO e registra il pattern dei sintomi e le letture ambientali.
    minutes: 2
  - id: co2_reassess
    en: Recheck CO2 and symptoms in 4 hours.
    it: Ricontrolla CO2 e sintomi dopo 4 ore.
    minutes: 1
---
## Purpose
Correct the shared environment before treating individual symptoms.

## Scope
Any crew member can start ventilation checks. CMO coordinates symptom assessment.
