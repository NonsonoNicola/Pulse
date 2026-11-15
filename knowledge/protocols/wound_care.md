---
id: protocol_wound_care
title: Wound and bleeding
title_it: Ferite e sanguinamento
status: NEEDS_CLINICAL_REVIEW
severity: orange
resources: [bandages, splint, urine_test_strips, medication_cabinet]
reassess_minutes: 120
escalate_when_en:
  - Bleeding does not stop with pressure
  - Deep, contaminated or bite wound
  - Numbness, loss of circulation, or signs of infection
escalate_when_it:
  - Il sanguinamento non si ferma con la pressione
  - Ferita profonda, contaminata o da morso
  - Intorpidimento, circolazione compromessa o segni di infezione
steps:
  - id: wound_pressure
    en: Apply direct pressure with a sterile dressing until bleeding stops.
    it: Applica pressione diretta con una garza sterile finché il sanguinamento si ferma.
    minutes: 5
  - id: wound_clean
    en: Clean the wound with the approved solution and remove visible debris.
    it: Pulisci la ferita con la soluzione approvata e rimuovi i corpi estranei visibili.
    minutes: 3
  - id: wound_dress
    en: Cover with a sterile dressing and check circulation beyond the injury.
    it: Copri con una garza sterile e controlla la circolazione a valle della ferita.
    minutes: 2
  - id: wound_cmo
    en: Contact the CMO and document mechanism, time and tetanus status.
    it: Contatta il CMO e documenta meccanismo, ora e stato della vaccinazione antitetanica.
    minutes: 2
  - id: wound_reassess
    en: Recheck bleeding, pain, colour and sensation in 2 hours.
    it: Ricontrolla sanguinamento, dolore, colore e sensibilità dopo 2 ore.
    minutes: 2
---
## Purpose
Control bleeding, prevent infection, and recognise injuries that need CMO-led care.

## Scope
Any crew member can start first aid.
