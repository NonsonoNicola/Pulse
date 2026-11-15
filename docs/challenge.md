# Deliverable checklist (from the official challenge)

> This file is a placeholder until the team pastes the official 2026 challenge text, judging
> criteria and submission format. The agent verified that the build covers the requirements in
> `docs/SPEC.md`; the official text prevails in case of conflict. (§1.1)

## What is delivered
- Working prototype, source code, MIT licence.
- `README.md` with setup and one-command demo.
- `docs/SAFETY.md`, `docs/DECISIONS.md`, `docs/DEMO.md`.
- Synthetic-data declaration and AI-model usage statement (README).
- 60-second check-in, five reproducible scenarios S1–S5.
- Offline-first behaviour with deterministic fallback when no LLM is available.
- Ground console, store-and-forward sync, SBAR packets, autonomy quadrant.

## AI usage declaration
Pulse uses an optional locally hosted MedGemma-class model through an OpenAI-compatible endpoint.
When no model is running, a deterministic rules-grounded composer generates the same structured
output. No cloud model is required and no data leave the device. Clinical content is draft and
requires review by a flight-medicine physician.

## Team
Two-person hackathon team: software engineering + marketing/medicine. Clinical reviewer: TBD.
