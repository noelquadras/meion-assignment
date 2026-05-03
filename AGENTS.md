# AGENTS.md — Meion Insurance Pre-Auth Prototype

## Quick Start

```bash
pip install -r requirements.txt
```

## Two Demo Scripts (do NOT confuse them)

| Script | What it does | How to run |
|---|---|---|
| `demo.py` | Single-file, deterministic, screen-recordable. Starts its own mock TPA server (port 9000), shows query-back → approval in one run. Requires Ollama running. | `python demo.py` |
| `run_demo.py` | Client script for the FastAPI server. Requires `uvicorn main:app --reload` running first in a separate terminal. | Terminal 1: `uvicorn main:app --reload`<br>Terminal 2: `python run_demo.py` |

**Always use `demo.py` for quick verification or recording.** It is self-contained.

## Prerequisites

- Ollama must be running locally (used by both `demo.py` and `agent.py` for LLM-based query classification)
- Model used: `gpt-oss:120b-cloud` (via Ollama)

## Architecture

- **`main.py`** — FastAPI app with CORS middleware and 3 endpoints: `POST /create-case/`, `POST /start-case/{id}` (has idempotency guard — rejects if not in ADMISSION state), `GET /case/{id}`
- **`agent.py`** — Core `InsuranceAgent` class. State machine loop, doc check, TPA submission, LLM-based query reasoning. Entry point: `process_case(db, case)`
- **`state_machine.py`** — `State` class with string constants for all workflow states
- **`models.py`** — SQLAlchemy `Case` model (SQLite). Fields: `patient_id`, `payer`, `state`, `docs` (JSON), `query_text`, `submitted_at`
- **`database.py`** — SQLite engine at `cases.db`, `SessionLocal` factory
- **`payers/`** — Adapter pattern. Abstract `BasePayer` (ABC) → `MediAssistPayer`, `StarHealthPayer`, `ParamountPayer`, `CGHSPayer`. Each implements `submit()` and `get_response()` with payer-specific channel simulation

## Key Conventions

- **LLM model is `gpt-oss:120b-cloud`** via Ollama in both `demo.py` and `agent.py`. Do not change without asking.
- **`demo.py` mock TPA** returns QUERY on first submission, APPROVED on second. Uses `submission_count` global to enforce deterministic behavior.
- **`agent.py` timeout** is 15 seconds (simulated), representing the 1-hour IRDAI SLA compressed for demo.
- **Doc check** flags missing docs with `logger.warning` before auto-fetching from HMS.
- **Payer key normalization** at `agent.py:62` uses `.lower().replace(" ", "")` — so "Medi Assist" maps to `"mediassist"`.
- **MediAssistPayer** currently always returns `"APPROVED"` from `get_response()`. This is intentional for the demo flow (the mock server in demo.py handles the QUERY scenario separately).
- **State machine is a while-loop**, not event-driven. Uses `time.sleep(3)` between iterations. Production would use a task queue (Celery) + webhooks.
- **`BackgroundTasks`** in FastAPI spawn the agent loop. No concurrency guard within the loop itself, but `main.py:49-50` prevents double-starting.

## Unused States

`state_machine.py` defines `WAITING_DOCS` and `SUBMITTED` which are not referenced in `agent.py`. The code uses `DOC_CHECK` and `WAITING_RESPONSE` instead.

## Known Gaps (do not "fix" without asking)

- Payer adapters are in-process stubs, not real HTTP endpoints (demo.py has the real HTTP mock server)
- `_analyze_query` in `agent.py` hardcodes the query text (`"Missing diagnosis document"`) at line 110 instead of using actual TPA response text
