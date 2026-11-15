# Pulse — NASA Space Apps 2026

**Physiological Universal Life Support Engine**

**Research prototype — not a medical device.**

Pulse is a lightweight health monitoring and decision-support system for long-duration spaceflight. It combines deterministic rule-based alerting, personal baseline analytics, crew-level pattern detection, and an optional local LLM (MedGemma 4B) with RAG over validated clinical protocols.

## Features

- **Deterministic alarms** — Rule engine evaluates vitals, symptoms, and environment against validated thresholds. Works with LLM offline.
- **Personal baselines** — Robust, gap-aware baselines per astronaut per metric. Freeze during orange/red alerts.
- **Crew-level findings** — Lagged permutation correlations detect shared environmental exposures (e.g., CO₂ drift).
- **LLM assistance** — Optional MedGemma 4B via OpenAI-compatible endpoint. Guardrails enforce protocol adherence, no dose numbers, citation validation.
- **Offline-first** — Runs entirely on-board after setup. Store-and-forward sync to ground node.
- **Five demo scenarios** — S1 CO₂ drift, S2 infection, S3 blackout+backfill, S4 emergency (link loss), S5 sensor fault.
- **Append-only event store** — Idempotent, tamper-evident, SQLite WAL.
- **Honest gamification** — Reporting streak, time-bank, sentinel badge, crew goals. No health-outcome rewards.

## Quick Start

```bash
# Clone and enter directory
cd Pulse

# One-command: setup + seed + run all services
make demo
```

This runs `make setup` (creates venv, installs deps), seeds demo data, and starts:
- Backend API at `http://127.0.0.1:8000`
- Ground console at `http://127.0.0.1:8001`
- Frontend at `http://127.0.0.1:5173`

## Manual Commands (if you want step by step)

```bash
make setup      # Install deps (Python 3.12 venv + npm) — run once
make seed       # Generate synthetic mission data
make dev        # Run backend + ground + frontend
make test       # Run test suite
make demo-check # Run scenario assertions
make clean      # Remove generated data
```

## Demo Accounts

| Username | Role | Astronaut |
|----------|------|-----------|
| `elena` | astronaut | Commander Elena Rossi |
| `maya` | cmo | Flight Engineer/CMO Maya Chen |
| `luca` | astronaut | Mission Specialist Luca Bianchi |
| `aiko` | astronaut | Mission Specialist Aiko Tanaka |
| `ground` | ground | Flight Surgeon Dr. Sarah Okafor |
| `admin` | admin | Mission Control Admin |

Password for all: `crewmd`

## Demo Scenarios

Run via the **Scenario Lab** in the frontend or via API:

```bash
# S2: Inject infection burst for Maya
curl -X POST -H "Cookie: crewmd_session=..." \
  -H "Content-Type: application/json" \
  -d '{"scenario":"S2","action":"inject"}' \
  http://127.0.0.1:8000/demo/scenario

# S3: Backfill Luca's missing days
curl -X POST ... -d '{"scenario":"S3","action":"backfill"}'

# S5: Add manual SpO2 recheck for Aiko
curl -X POST ... -d '{"scenario":"S5","action":"recheck"}'
```

**Expected outcomes:**
- **S1 (default)**: All 4 yellow, crew finding (4/4), CO₂ orange alert, CO₂ correlation high
- **S2**: Maya → orange (temp + HR), resting HR yellow
- **S3**: Luca gray → yellow, coverage 0.27 → 0.93, backfilled_recent=true
- **S4**: Emergency case opened, SBAR queued, autonomy mode simulated via link slider
- **S5**: Aiko yellow + sensor quality flag, manual SpO2 recheck suggested, never red

## Codespaces (1 click, zero install)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/NonsonoNicola/Pulse)

> Click badge → wait for build → `make demo` → 3 clickable URLs

## Demo Links (click = scenario injected in REAL system)

| Scenario | Link | What you see |
|----------|------|--------------|
| S1 — CO₂ drift (default) | `/?demo=S1` | 4 yellow, crew finding 4/4, CO₂ orange r=0.96 |
| S2 — Maya infection | `/?demo=S2` | Maya orange (skin_temp +1.1°C) |
| S3 — Luca blackout | `/?demo=S3` | Luca gray→yellow, coverage 0.27→0.93 |
| S4 — Chest pain emergency | `/?demo=S4` | Protocol stepper + SBAR queued |
| S5 — Aiko sensor fault | `/?demo=S5` | Aiko yellow + sensor quality, never red |
| Ground Console | `/ground` | Cases, sync queue, link slider, reply |

## Safety & Compliance

- All clinical content marked `NEEDS_CLINICAL_REVIEW`
- Deterministic rules = alarm source; LLM only raises caution
- No dose numbers in free text (guardrails enforced)
- Disclaimers on every clinical screen
- Appendix: `docs/SAFETY.md`, `docs/DEMO.md`, `docs/DECISIONS.md`

## Tech Stack

- **Backend**: Python 3.12 / FastAPI / SQLite WAL
- **Frontend**: React 18 / TypeScript / Vite / Tailwind / Recharts
- **LLM**: MedGemma 4B via OpenAI-compatible endpoint (fallback mode demo)
- **Deterministic rules engine** (11 rules) — works with LLM offline

## License

MIT — see `LICENSE`.