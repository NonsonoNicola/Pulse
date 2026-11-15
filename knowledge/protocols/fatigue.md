---
id: protocol_fatigue
title: Persistent fatigue
title_it: Affaticamento persistente
status: NEEDS_CLINICAL_REVIEW
severity: yellow
resources: [thermometer, bp_cuff, scale]
reassess_minutes: 1440
escalate_when_en:
  - Fever, chest pain, breathlessness or fainting
  - Fatigue interferes with safety-critical tasks
  - No improvement after several days of reduced load
escalate_when_it:
  - Febbre, dolore al petto, fiato corto o svenimento
  - La stanchezza interferisce con compiti critici per la sicurezza
  - Nessun miglioramento dopo giorni di carico ridotto
steps:
  - id: fatigue_review
    en: Review the last 7 days of sleep, workload and exercise with the CMO.
    it: Rivedi con il CMO gli ultimi 7 giorni di sonno, carico di lavoro ed esercizio.
    minutes: 5
  - id: fatigue_rest
    en: Reduce non-essential tasks and protect the next sleep window.
    it: Riduci le attività non essenziali e proteggi la prossima finestra di sonno.
    minutes: 1
  - id: fatigue_hydrate
    en: Check hydration and drink regularly.
    it: Controlla l'idratazione e bevi regolarmente.
    minutes: 1
  - id: fatigue_screen
    en: Measure temperature and resting heart rate. Ask about breathlessness, chest pain and mood.
    it: Misura temperatura e frequenza a riposo. Chiedi di fiato corto, dolore al petto e umore.
    minutes: 3
  - id: fatigue_reassess
    en: Reassess energy and function after one day of reduced load.
    it: Rivaluta energia e funzione dopo un giorno di carico ridotto.
    minutes: 1
---
## Purpose
Separate ordinary fatigue from a developing medical or psychological problem.

## Scope
Self-care plus CMO review if persistent.
