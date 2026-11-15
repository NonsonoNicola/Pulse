# Pulse Demo Guide

## 5-Minute Demo Script

### 1. Problem & Why Now (30s)
> "Astronauts on deep-space missions lose real-time contact with flight surgeons. They're not doctors, they minimize symptoms, and microgravity creates novel risks. Pulse gives them a lightweight monitor that works offline, detects both individual and shared environmental risks, and guides them through validated protocols — with or without Earth."

### 2. Home & 60-Second Check-in (60s)
1. Login as `elena` / `crewmd`
2. **Home screen**: Traffic-light status (yellow), today's task (blood pressure test), daily ring (✓ check-in), honesty streak (51 days), time saved (66 min)
3. Tap **Check-in**: 5-level neutral scales (mood/energy/sleep), symptom toggles, optional note
4. Submit → summary shows test suggestion with "why", honesty streak increments

### 3. S1 — Crew CO₂ Drift (60s)
- **Already active** on fresh seed
- Elena's status: Yellow (HRV -25%, sleep <6.5h)
- Crew view (login as `ground`): 4/4 yellow, **crew finding** (4 members, HRV↓ sleep↓ symptoms↑ HR↑)
- **Environmental alert**: CO₂ orange (2284 ppm, 3 days)
- **Correlation**: Cabin CO₂ r=+0.96, same day, n=30, p=0.003 — high confidence
- **Insight**: "Treating the shared environment is the first lever"

### 4. S3 — Blackout & Backfill (60s)
- Luca shows **Gray** (coverage 27%, 3-day gap)
- Run **Scenario Lab → S3 Backfill**
- Luca → **Yellow** (HRV -19%, sleep <6.5h), coverage 93%, `backfilled_recent=true`
- Timeline shows backfilled days with "Backfilled from wearable after comms blackout"

### 5. S4 — Emergency in Autonomy (60s)
- Login as `elena`, open **Emergency**, select "Chest pain"
- Protocol steps appear one at a time: Sit → Repeat SpO₂ → Call CMO → Check environment → Prepare O₂ → SBAR → Reassess
- **SBAR packet** auto-generated, queued for sync
- **Link slider** (top bar): Live (5s) → Async (15 min) → Assisted (6h) → Full autonomy
- Ground console (`ground`): Case appears in queue, flight surgeon replies, onboard re-evaluates

### 6. S5 — Faulty Sensor + Bias (30s)
- Aiko: Yellow (sleep), **sensor quality flag** (SpO₂ discordant with HR/RR)
- Suggested test: **Manual SpO₂ recheck** (1 min)
- Run **Scenario Lab → S5 Recheck** → manual SpO₂ 98% added
- **Never goes red** from faulty sensor; rule is yellow, guardrails prevent escalation

### 7. Limits & Ethics (30s)
> "Research prototype. All clinical content NEEDS_CLINICAL_REVIEW. Deterministic rules are the alarm source — LLM only raises caution. No dose numbers in chat. Input treated as data, never instructions. Designed for space; applies to polar stations, submarines, remote clinics, disaster zones."

### 8. Earth Impact (15s)
> "Same stack: offline monitoring, store-and-forward, protocol guidance, local LLM. Validated in analog missions (HERA, SIRIUS, :envihab). Next: integrate NASA biomedical datasets, flight-certified hardware."

---

## API Endpoints for Demo Automation

```bash
# Health
curl http://127.0.0.1:8000/health

# Login
curl -X POST -H "Content-Type: application/json" \
  -d '{"username":"ground","password":"crewmd"}' \
  http://127.0.0.1:8000/auth/login

# Status (as ground)
TOKEN=<from login>
curl -H "Cookie: crewmd_session=$TOKEN" \
  http://127.0.0.1:8000/astronauts/astronaut_01/status

# Crew summary
curl -H "Cookie: crewmd_session=$TOKEN" \
  http://127.0.0.1:8000/crew/summary

# Chat
curl -X POST -H "Cookie: crewmd_session=$TOKEN" -H "Content-Type: application/json" \
  -d '{"astronaut_id":"astronaut_01","message":"How is the crew?"}' \
  http://127.0.0.1:8000/chat

# Scenarios
curl -X POST -H "Cookie: crewmd_session=$TOKEN" -H "Content-Type: application/json" \
  -d '{"scenario":"S2","action":"inject"}' \
  http://127.0.0.1:8000/demo/scenario

curl -X POST ... -d '{"scenario":"S3","action":"backfill"}'
curl -X POST ... -d '{"scenario":"S5","action":"recheck"}'

# Emergency
curl -X POST ... -d '{"astronaut_id":"astronaut_01","protocol_key":"chest_pain","reason":"Chest pain radiating to left arm"}' \
  http://127.0.0.1:8000/emergency/start

# Booklet export
curl -H "Cookie: crewmd_session=$TOKEN" \
  http://127.0.0.1:8000/booklet/astronaut_01/export \
  -o booklet_astronaut_01.zip
```

---

## Expected Assertions (for `make demo-check`)

| Scenario | Astronaut | Level | Key Assertions |
|----------|-----------|-------|----------------|
| S1 (seed) | Elena | yellow | HRV -25%, sleep <6.5h |
| S1 (seed) | Maya | yellow | HRV -22%, sleep <6.5h |
| S1 (seed) | Luca | gray | coverage <0.4 |
| S1 (seed) | Aiko | yellow | sensor quality flag, SpO₂ suspect |
| S1 (seed) | Crew | — | finding 4/4, CO₂ orange, corr r>0.8 p<0.01 |
| S2 (inject) | Maya | orange | skin_temp >1.0°C dev, HR yellow |
| S3 (backfill) | Luca | yellow | coverage >0.8, backfilled_recent=true |
| S4 (emergency) | Elena | red | case opened, SBAR queued, sync queued |
| S5 (recheck) | Aiko | yellow | sensor quality flag, manual_spo2_recheck test, not red |

---

## Frontend Pages (P0)

| Route | Purpose |
|-------|---------|
| `/login` | Multi-account, persistent session |
| `/` | Home: traffic light, daily ring, honesty streak, time saved, task |
| `/checkin` | 5-section flow, neutral scales, symptom toggles, skip option |
| `/chat` | Streaming LLM, evidence chips, protocol steps, disclaimer |
| `/trends` | Recharts lines, personal baseline bands, quality dots |
| `/crew` | Aggregates only, crew finding, env alerts, no individual data |
| `/booklet` | Timeline, profile, tests, reports, export zip |
| `/emergency` | Protocol stepper, SBAR status, link slider |
| `/recover` | Calendar heatmap, backfill button, conflict resolution |
| `/access` | Role matrix, emergency override log |
| `/profile` | Locale, explanation level, data export |
| `/ground` | Sync queue, link status, latency slider (admin) |
| `/scenario-lab` | S1-S5 inject/backfill/recheck buttons |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `make demo` hangs | `make clean && make demo` |
| LLM unavailable | Expected — runs in fallback mode (see `/health`) |
| Port 8000/8001/5173 in use | Kill existing: `pkill -f uvicorn; pkill -f vite` |
| DB locked | Remove `data/crewmd.db-wal`, `data/crewmd.db-shm` |
| Frontend blank | `cd frontend && npm run build` then `npm run dev` |

---

## Video / Screenshots Checklist

- [ ] Home screen with yellow status + daily ring
- [ ] Check-in flow (3 taps per section)
- [ ] Chat with evidence chips + disclaimer
- [ ] Crew view with finding + CO₂ correlation
- [ ] Trends with baseline bands
- [ ] Emergency stepper + SBAR
- [ ] Scenario Lab: S2 inject → Maya orange
- [ ] Scenario Lab: S3 backfill → Luca yellow
- [ ] Scenario Lab: S5 recheck → Aiko yellow + test
- [ ] Booklet export zip contents
- [ ] Ground console: case queue + reply
- [ ] Link slider: Live → Async → Assisted → Full