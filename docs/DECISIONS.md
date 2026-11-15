# Pulse — decisions log

Format: date · decision · rationale · spec reference.

## 2026-11-14 · Repository layout
The repository root is `crewmd/`. The working directory of the session contains it to keep the
hackathon workspace clean. `make dev` runs from `crewmd/`.

## 2026-11-14 · Python 3.12
The machine has Python 3.9 (system) and Homebrew Python 3.12. The latter is used; the Makefile
falls back to `python3 -m venv` when Homebrew Python is unavailable. Spec asks for 3.11+.

## 2026-11-14 · SQLite via stdlib `sqlite3`
Instead of SQLAlchemy/SQLModel, the event store uses stdlib `sqlite3` in WAL mode with explicit SQL.
Rationale: smaller dependency surface, easier to prove append-only triggers, deterministic tests.
The event envelope and API are unaffected. (§5.2, §6)

## 2026-11-14 · Analysis without SciPy/pandas
Daily features and robust baselines use NumPy and plain Python. The crew-environment correlation
uses Pearson r with a seeded permutation test implemented in NumPy. This covers the P0 statistical
claims without heavy dependencies. (§7.5)

## 2026-11-14 · Deterministic vector store + retrieval
Chroma/sentence-transformers are optional and not installed by default. The `VectorStore` interface
has a deterministic local implementation: hashed multilingual token embeddings + BM25-style keyword
scoring, fused for hybrid retrieval. This keeps setup fully offline and repeatable; a
`SentenceTransformerEmbedder` can be enabled later without changing callers. (§5.2, §9.3)

## 2026-11-14 · No MedGemma binary in the repo
No local model runtime is present on the development machine. `LLMClient` speaks the OpenAI-compatible
API (Ollama or llama.cpp). When unavailable, `RulesComposer` produces the same validated structured
assessment from rules, signatures, protocols and RAG cards. The UI always shows which mode is active.
This is the specified L0 degradation path. (§10.8, §4)

## 2026-11-14 · Ground node in the same codebase, separate process
The ground node is a separate FastAPI app (`app.ground_main`) with its own SQLite database and a
minimal server-rendered flight-surgeon console on :8001. This satisfies "separate service" without
duplicating domain models. (§11.6)

## 2026-11-14 · Emergency override visibility
When a red case opens, the CMO and ground user can see the relevant data. The patient's own view
always states: "Emergency access opened for the CMO and flight surgeon. Logged in the audit trail."
No promise of privacy the system cannot keep. (§2.1, §14)

## 2026-11-14 · Session auth
Local accounts with PBKDF2 password hashes and HttpOnly session cookies. Demo credentials are
listed on the login screen. No secrets in the repo. (§4, §14)

## 2026-11-14 · Demo clock
Synthetic events are anchored to the seed time. The scenario lab can inject S1–S5 on demand.
`make demo` seeds a 60-day history with S1, an S3 gap, and S5 sensor fault already visible; S2
and S4 are triggered from the Scenario Lab so the presenter can show the transition live. (§2.3, §16)

## 2026-11-14 · Remote updates simplified
Update packages use a versioned manifest with SHA-256 hashes and an HMAC-SHA256 signature marked
`SIMULATED_SIGNATURE` (Ed25519 key management is out of scope for the demo). Apply/rollback,
health check and zero-loss event tests are implemented for the knowledge base channel. (§11.7, P1)

## 2026-11-14 · PDF/voice/image features are P1
Not implemented in the 48h build: PDF export, real speech-to-text, MedGemma vision. The data model
reserves event types (`voice_report`, `image_report`) and UI entry points are marked "roadmap".
Per §15 these are the first items to cut. (§FR-13, FR-14, FR-21)
