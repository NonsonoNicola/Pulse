---
id: protocol_dehydration
title: Dehydration
title_it: Disidratazione
status: NEEDS_CLINICAL_REVIEW
severity: orange
resources: [oral_rehydration_salts, urine_test_strips, scale, bp_cuff, iv_fluids]
reassess_minutes: 120
escalate_when_en:
  - Inability to keep fluids down
  - Confusion, fainting or very low urine output
  - Rapid weight loss or signs of shock
escalate_when_it:
  - Incapacità di trattenere i liquidi
  - Confusione, svenimento o urine molto scarse
  - Rapida perdita di peso o segni di shock
steps:
  - id: dehydrate_assess
    en: Check urine colour, fluid intake, weight and standing symptoms.
    it: Controlla colore delle urine, liquidi assunti, peso e sintomi in piedi.
    minutes: 3
  - id: dehydrate_drink
    en: Drink small amounts frequently. Use oral rehydration salts if losses are significant.
    it: Bevi piccoli sorsi frequentemente. Usa sali reidratanti se le perdite sono importanti.
    minutes: 1
  - id: dehydrate_cmo
    en: Contact the CMO if vomiting, diarrhoea, fainting or unable to drink.
    it: Contatta il CMO se c'è vomito, diarrea, svenimento o impossibilità di bere.
    minutes: 1
  - id: dehydrate_reassess
    en: Recheck urine output and symptoms in 2 hours.
    it: Ricontrolla urine e sintomi dopo 2 ore.
    minutes: 1
---
## Purpose
Restore fluids safely and recognise when oral intake is not enough.

## Scope
Self-care with CMO escalation. IV fluids require CMO direction.
